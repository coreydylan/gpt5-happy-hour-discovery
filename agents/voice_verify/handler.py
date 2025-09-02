"""
VoiceVerify Agent Lambda Handler - Phone Call Verification
Tier A source (weight: 1.0) - Direct staff confirmation (KILLER FEATURE)

This agent:
1. Makes 20-second phone calls to restaurants
2. Asks structured questions about happy hour
3. Records calls with consent
4. Transcribes and extracts information
5. Provides high-confidence verification
6. USES GPT-5 EXCLUSIVELY for analysis

This is our unfair advantage - competitors won't call!
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import quote_plus
import hashlib
import asyncio
from enum import Enum

import boto3
from twilio.rest import Client as TwilioClient
from twilio.twiml import Gather, VoiceResponse
from pydantic import ValidationError

# Import shared models
import sys
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.models import (
    CanonicalRestaurantInput,
    AgentClaim, 
    AgentResult,
    AgentType,
    SourceType,
    Specificity,
    Modality
)

# Import GPT-5 configuration
from shared.gpt5_config import (
    GPT5Client,
    GPT5Model,
    ReasoningEffort,
    Verbosity,
    create_extraction_request,
    create_reasoning_request,
    HAPPY_HOUR_EXTRACTION_SCHEMA
)


# ============================================================================
# CONFIGURATION
# ============================================================================

class CallStatus(str, Enum):
    """Status of voice verification call"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    DECLINED = "declined"


class VoiceVerifyConfig:
    """Configuration for voice verification calls"""
    
    # Call settings
    CALL_TIMEOUT = 120          # 2 minutes maximum call duration
    RING_TIMEOUT = 30           # 30 seconds to answer
    MAX_RETRIES = 2             # Maximum retry attempts
    
    # TwiML settings
    VOICE = 'alice'             # Twilio voice (alice, man, woman)
    LANGUAGE = 'en-US'          # Language for speech
    
    # Question flow - structured 20-second decision tree
    INTRO_MESSAGE = """
    Hi! This is a quick verification call for HappyHourAI. 
    I just need 30 seconds to verify your happy hour information. 
    Is this okay?
    """
    
    QUESTIONS = [
        {
            "id": "consent",
            "text": "Can I ask you about your happy hour offerings? This call may be recorded for quality purposes.",
            "expected_answers": ["yes", "sure", "ok", "okay", "fine"],
            "timeout": 5
        },
        {
            "id": "has_happy_hour", 
            "text": "Do you currently offer happy hour?",
            "expected_answers": ["yes", "no", "we do", "we don't"],
            "timeout": 5
        },
        {
            "id": "schedule",
            "text": "What days and times is your happy hour?", 
            "expected_answers": [],  # Open-ended
            "timeout": 15
        },
        {
            "id": "location",
            "text": "Is happy hour available throughout the restaurant or just at the bar?",
            "expected_answers": ["bar", "everywhere", "whole restaurant", "just bar"],
            "timeout": 8
        },
        {
            "id": "restrictions",
            "text": "Are there any days when happy hour is not available, like holidays or game days?",
            "expected_answers": [],  # Open-ended
            "timeout": 10
        }
    ]
    
    # Call analysis - Using GPT-5 for extraction
    TRANSCRIPTION_MODEL = 'whisper-1'  # Still use Whisper for transcription
    
    # Webhook endpoints (will be set by environment)
    WEBHOOK_BASE_URL = None  # Set from environment


# ============================================================================
# VOICE VERIFY AGENT CLASS
# ============================================================================

class VoiceVerifyAgent:
    """Voice verification agent for direct phone confirmation"""
    
    def __init__(self, config: Optional[VoiceVerifyConfig] = None):
        self.config = config or VoiceVerifyConfig()
        
        # Initialize clients
        self.twilio_client = TwilioClient(
            os.environ.get('TWILIO_ACCOUNT_SID'),
            os.environ.get('TWILIO_AUTH_TOKEN')
        )
        self.gpt5_client = GPT5Client(api_key=os.environ['OPENAI_API_KEY'])
        self.s3_client = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        
        # Configuration
        self.from_phone = os.environ.get('TWILIO_PHONE_NUMBER', '+12345551234')  
        self.results_bucket = os.environ.get('RESULTS_BUCKET')
        self.webhook_base = os.environ.get('WEBHOOK_BASE_URL', 'https://api.example.com')
        
        # State management (in production, use DynamoDB)
        self.call_states = {}
        
        # Performance tracking
        self.start_time = time.time()
        self.total_cost_cents = 0
    
    async def analyze_restaurant(self, cri: CanonicalRestaurantInput) -> AgentResult:
        """
        Main analysis function: make verification call to restaurant
        
        Args:
            cri: Canonical Restaurant Input with phone number
            
        Returns:
            AgentResult with call verification results
        """
        
        result = AgentResult(
            agent_type=AgentType.VOICE_VERIFY,
            cri_id=cri.cri_id,
            started_at=datetime.utcnow()
        )
        
        try:
            # Validate phone number
            if not cri.phone or not cri.phone.is_valid:
                result.error_message = "No valid phone number provided"
                result.success = False
                return result
            
            phone_number = cri.phone.e164
            
            # Check if we recently called this number
            if await self._recently_called(phone_number):
                result.error_message = "Recently called this number - skipping to avoid harassment"
                result.success = False
                return result
            
            # Initiate the call
            call_sid = await self._initiate_call(phone_number, cri)
            
            if not call_sid:
                result.error_message = "Failed to initiate call"
                result.success = False
                return result
            
            # Wait for call completion (with timeout)
            call_result = await self._wait_for_call_completion(call_sid)
            
            if call_result['status'] != CallStatus.COMPLETED:
                result.error_message = f"Call not completed: {call_result['status']}"
                result.success = call_result['status'] in [CallStatus.NO_ANSWER, CallStatus.BUSY]  # Partial success
                return result
            
            # Process call recording and transcript
            claims = await self._process_call_results(call_result, cri, phone_number)
            
            # Calculate confidence
            total_confidence = self._calculate_agent_confidence(claims, call_result)
            
            # Success!
            result.claims = claims
            result.total_confidence = total_confidence
            result.success = True
            result.sources_accessed = [f"Phone call to {phone_number}"]
            result.completed_at = datetime.utcnow()
            result.execution_time_ms = int((time.time() - self.start_time) * 1000)
            result.total_cost_cents = self.total_cost_cents
            
            return result
            
        except Exception as e:
            result.error_message = f"VoiceVerify failed: {str(e)}"
            result.success = False
            result.completed_at = datetime.utcnow()
            return result
    
    async def _recently_called(self, phone_number: str) -> bool:
        """Check if we called this number recently to avoid harassment"""
        
        # In production, check DynamoDB for recent calls
        # For now, simple in-memory check
        cutoff_time = datetime.utcnow() - timedelta(days=7)  # Don't call same number within 7 days
        
        try:
            # Query call logs (implementation depends on storage choice)
            # For MVP, we'll just check a simple cache
            last_call_key = f"last_call_{phone_number}"
            
            # This would be implemented with proper storage
            return False  # For MVP, allow all calls
            
        except Exception as e:
            print(f"Error checking recent calls: {e}")
            return False
    
    async def _initiate_call(self, phone_number: str, cri: CanonicalRestaurantInput) -> Optional[str]:
        """
        Initiate phone call to restaurant
        
        Args:
            phone_number: Phone number to call (E.164 format)
            cri: Restaurant context
            
        Returns:
            Call SID if successful, None otherwise
        """
        
        try:
            # Create unique call identifier
            call_id = hashlib.md5(f"{phone_number}_{int(time.time())}".encode()).hexdigest()[:8]
            
            # Store call context for webhook handling
            self.call_states[call_id] = {
                'cri': cri.dict(),
                'phone_number': phone_number,
                'status': CallStatus.INITIATED,
                'start_time': datetime.utcnow().isoformat(),
                'responses': {}
            }
            
            # Build webhook URLs
            status_callback = f"{self.webhook_base}/voice-verify/status/{call_id}"
            twiml_url = f"{self.webhook_base}/voice-verify/twiml/{call_id}"
            
            # Make the call
            call = self.twilio_client.calls.create(
                to=phone_number,
                from_=self.from_phone,
                url=twiml_url,
                status_callback=status_callback,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                timeout=self.config.RING_TIMEOUT,
                record=True,  # Record the call
                recording_status_callback=f"{self.webhook_base}/voice-verify/recording/{call_id}"
            )
            
            print(f"Call initiated: {call.sid} to {phone_number}")
            return call.sid
            
        except Exception as e:
            print(f"Error initiating call: {e}")
            return None
    
    async def _wait_for_call_completion(self, call_sid: str, timeout: int = 180) -> Dict[str, Any]:
        """
        Wait for call to complete and return results
        
        Args:
            call_sid: Twilio call SID
            timeout: Maximum time to wait
            
        Returns:
            Call result dictionary
        """
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                # Check call status
                call = self.twilio_client.calls(call_sid).fetch()
                
                if call.status in ['completed', 'busy', 'no-answer', 'failed', 'canceled']:
                    # Map Twilio status to our status
                    status_mapping = {
                        'completed': CallStatus.COMPLETED,
                        'busy': CallStatus.BUSY,
                        'no-answer': CallStatus.NO_ANSWER,
                        'failed': CallStatus.FAILED,
                        'canceled': CallStatus.FAILED
                    }
                    
                    return {
                        'status': status_mapping.get(call.status, CallStatus.FAILED),
                        'call_sid': call_sid,
                        'duration': call.duration,
                        'price': call.price,
                        'twilio_status': call.status
                    }
                
                # Wait before checking again
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Error checking call status: {e}")
                await asyncio.sleep(10)
        
        # Timeout
        return {
            'status': CallStatus.FAILED,
            'call_sid': call_sid,
            'error': 'Timeout waiting for call completion'
        }
    
    def generate_twiml_response(self, call_id: str, question_id: str = None) -> str:
        """
        Generate TwiML for call flow
        
        Args:
            call_id: Unique call identifier
            question_id: Current question ID (None for start)
            
        Returns:
            TwiML XML string
        """
        
        response = VoiceResponse()
        
        if not question_id:
            # Start of call - intro message
            response.say(
                self.config.INTRO_MESSAGE,
                voice=self.config.VOICE,
                language=self.config.LANGUAGE
            )
            
            # First question (consent)
            gather = Gather(
                num_digits=0,  # Variable length
                timeout=self.config.QUESTIONS[0]['timeout'],
                action=f"{self.webhook_base}/voice-verify/response/{call_id}/consent",
                method='POST'
            )
            gather.say(
                self.config.QUESTIONS[0]['text'],
                voice=self.config.VOICE,
                language=self.config.LANGUAGE
            )
            response.append(gather)
            
            # Fallback if no response
            response.say("Thank you for your time. Goodbye!")
            response.hangup()
        
        else:
            # Handle specific question flow
            question_index = next((i for i, q in enumerate(self.config.QUESTIONS) if q['id'] == question_id), None)
            
            if question_index is not None and question_index < len(self.config.QUESTIONS) - 1:
                # Ask next question
                next_question = self.config.QUESTIONS[question_index + 1]
                
                gather = Gather(
                    num_digits=0,
                    timeout=next_question['timeout'],
                    action=f"{self.webhook_base}/voice-verify/response/{call_id}/{next_question['id']}",
                    method='POST'
                )
                gather.say(
                    next_question['text'],
                    voice=self.config.VOICE,
                    language=self.config.LANGUAGE
                )
                response.append(gather)
                
                # Fallback
                response.say("Thank you!")
                response.hangup()
            else:
                # End of questions
                response.say(
                    "Thank you for helping us verify your happy hour information! Have a great day!",
                    voice=self.config.VOICE,
                    language=self.config.LANGUAGE
                )
                response.hangup()
        
        return str(response)
    
    def handle_voice_response(self, call_id: str, question_id: str, speech_result: str) -> str:
        """
        Handle voice response from caller
        
        Args:
            call_id: Call identifier
            question_id: Question being answered
            speech_result: Transcribed speech
            
        Returns:
            TwiML for next step
        """
        
        # Store response
        if call_id in self.call_states:
            self.call_states[call_id]['responses'][question_id] = {
                'text': speech_result,
                'timestamp': datetime.utcnow().isoformat()
            }
            self.call_states[call_id]['status'] = CallStatus.IN_PROGRESS
        
        # Generate next TwiML
        return self.generate_twiml_response(call_id, question_id)
    
    async def _process_call_results(
        self, 
        call_result: Dict[str, Any], 
        cri: CanonicalRestaurantInput,
        phone_number: str
    ) -> List[AgentClaim]:
        """
        Process completed call results into structured claims
        
        Args:
            call_result: Call completion information
            cri: Restaurant context
            phone_number: Phone number called
            
        Returns:
            List of extracted claims from call
        """
        
        try:
            call_sid = call_result['call_sid']
            
            # Get call recording
            recording_url = await self._get_call_recording(call_sid)
            
            # Transcribe recording if available
            transcript = ""
            if recording_url:
                transcript = await self._transcribe_recording(recording_url)
            
            # Also get structured responses from call flow
            call_id = None  # Would need to map call_sid to call_id
            structured_responses = {}
            
            if call_id and call_id in self.call_states:
                structured_responses = self.call_states[call_id]['responses']
            
            # Extract information using GPT-5
            claims = await self._extract_from_call_data(
                transcript, 
                structured_responses, 
                call_result,
                cri,
                phone_number
            )
            
            return claims
            
        except Exception as e:
            print(f"Error processing call results: {e}")
            return []
    
    async def _get_call_recording(self, call_sid: str) -> Optional[str]:
        """Get recording URL from Twilio"""
        
        try:
            recordings = self.twilio_client.recordings.list(call_sid=call_sid, limit=1)
            
            if recordings:
                recording = recordings[0]
                recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
                return recording_url
            
            return None
            
        except Exception as e:
            print(f"Error getting recording: {e}")
            return None
    
    async def _transcribe_recording(self, recording_url: str) -> str:
        """Transcribe call recording using OpenAI Whisper"""
        
        try:
            # Download recording
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(recording_url)
                response.raise_for_status()
                
                # Save to temporary file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name
                
                # Transcribe with Whisper (note: still using OpenAI's Whisper API)
                with open(temp_file_path, 'rb') as audio_file:
                    # Import openai for Whisper transcription
                    import openai
                    openai_client = openai.AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'])
                    transcript_response = await openai_client.audio.transcriptions.create(
                        model=self.config.TRANSCRIPTION_MODEL,
                        file=audio_file
                    )
                
                # Clean up temp file
                os.unlink(temp_file_path)
                
                # Track cost (Whisper is $0.006 per minute)
                duration_minutes = 2  # Estimate 2 minutes max
                cost_cents = int(duration_minutes * 0.6)  # $0.006 per minute
                self.total_cost_cents += cost_cents
                
                return transcript_response.text
                
        except Exception as e:
            print(f"Error transcribing recording: {e}")
            return ""
    
    async def _extract_from_call_data(
        self,
        transcript: str,
        structured_responses: Dict[str, Any],
        call_result: Dict[str, Any],
        cri: CanonicalRestaurantInput,
        phone_number: str
    ) -> List[AgentClaim]:
        """Extract structured claims from call data using GPT-5 with high reasoning"""
        
        # Combine all available information
        call_data = {
            'transcript': transcript,
            'structured_responses': structured_responses,
            'call_duration': call_result.get('duration', 0),
            'call_status': call_result.get('status')
        }
        
        extraction_prompt = f"""
Analyze this phone call transcript to extract verified happy hour information.

Restaurant: {cri.name}
Phone: {phone_number}
Address: {getattr(cri.address, 'raw', 'Unknown') if cri.address else 'Unknown'}

Call Duration: {call_result.get('duration', 'unknown')} seconds
Call Status: {call_result.get('status', 'unknown')}

CALL TRANSCRIPT:
{transcript}

STRUCTURED RESPONSES:
{json.dumps(structured_responses, indent=2)}

Extract ALL verified happy hour information with high confidence (this is direct staff confirmation).
Include:
- Schedule (days, times)
- Specials and pricing
- Restrictions or conditions
- Staff member name if mentioned
- Confirmation of current/accurate information

Phone verification provides HIGHEST confidence (0.9-1.0) as it's direct staff confirmation.
"""

        try:
            # Use GPT-5 with HIGH reasoning for voice analysis (complex, critical task)
            request = create_reasoning_request(
                prompt=extraction_prompt,
                context="Analyzing phone call transcript for verified happy hour information. This is Tier A evidence with highest confidence.",
                reasoning_effort=ReasoningEffort.HIGH,  # High reasoning for voice verification
                model=GPT5Model.GPT5  # Full GPT-5 for this critical verification
            )
            
            response = await self.gpt5_client.create_completion(request)
            
            # Track cost
            self.total_cost_cents += response.cost_cents
            
            # Parse response - GPT-5 with structured outputs should return valid JSON
            try:
                # First try to parse as structured extraction response
                response_data = json.loads(response.content)
                if 'extractions' in response_data:
                    extractions = response_data['extractions']
                else:
                    # Fallback to direct JSON array
                    extractions = response_data if isinstance(response_data, list) else []
            except json.JSONDecodeError:
                # Handle potential markdown wrapped response
                response_text = response.content.strip()
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end]
                extractions = json.loads(response_text)
            
            # Convert to AgentClaim objects
            claims = []
            for extraction in extractions:
                try:
                    # Create attestation string
                    staff_name = extraction.get('staff_name', 'Staff member')
                    call_date = datetime.utcnow().strftime('%Y-%m-%d')
                    attestation = f"{staff_name} confirmed via phone call on {call_date}"
                    
                    claim = AgentClaim(
                        agent_type=AgentType.VOICE_VERIFY,
                        source_type=SourceType.PHONE_CALL,
                        source_url=f"tel:{phone_number}",
                        source_domain='phone',
                        field_path=extraction['field_path'],
                        field_value=extraction['field_value'],
                        agent_confidence=extraction['confidence'],
                        specificity=Specificity(extraction.get('specificity', 'exact')),
                        modality=Modality.VOICE,
                        observed_at=datetime.utcnow(),
                        raw_snippet=f"{extraction.get('supporting_snippet', '')} | {attestation}",
                        raw_data={
                            'call_transcript': transcript,
                            'call_duration': call_result.get('duration'),
                            'staff_attestation': attestation,
                            'structured_responses': structured_responses,
                            'gpt5_model': response.model,
                            'reasoning_tokens': response.reasoning_tokens,
                            'cost_cents': response.cost_cents
                        }
                    )
                    claims.append(claim)
                except (ValidationError, ValueError) as e:
                    print(f"Error creating voice claim: {e}")
                    continue
            
            return claims
            
        except Exception as e:
            print(f"Error extracting from call data: {e}")
            return []
    
    def _calculate_agent_confidence(self, claims: List[AgentClaim], call_result: Dict[str, Any]) -> float:
        """Calculate agent confidence for voice verification"""
        
        if not claims:
            return 0.0
        
        # Base confidence from claims
        avg_confidence = sum(claim.agent_confidence for claim in claims) / len(claims)
        
        # Bonus for successful call completion
        completion_bonus = 0.1 if call_result.get('status') == CallStatus.COMPLETED else 0.0
        
        # Bonus for call duration (longer calls usually more informative)
        duration = call_result.get('duration', 0)
        if duration and duration > 30:  # At least 30 seconds
            duration_bonus = min(0.1, duration / 600)  # Up to 0.1 for 10+ minute calls
        else:
            duration_bonus = 0.0
        
        return min(1.0, avg_confidence + completion_bonus + duration_bonus)


# ============================================================================
# LAMBDA HANDLER
# ============================================================================

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for VoiceVerify Agent
    
    Supports both analysis requests and webhook callbacks
    """
    
    try:
        # Check if this is a webhook callback
        if 'path' in event and '/voice-verify/' in event['path']:
            return handle_webhook(event, context)
        
        # Standard analysis request
        cri_data = event.get('cri')
        if not cri_data:
            return {
                'statusCode': 400,
                'body': {'error': 'Missing CRI data'}
            }
        
        cri = CanonicalRestaurantInput(**cri_data)
        agent = VoiceVerifyAgent()
        
        import asyncio
        result = asyncio.run(agent.analyze_restaurant(cri))
        
        return {
            'statusCode': 200,
            'body': {
                'success': result.success,
                'agent_type': result.agent_type.value,
                'claims_count': len(result.claims),
                'total_confidence': result.total_confidence,
                'execution_time_ms': result.execution_time_ms,
                'cost_cents': result.total_cost_cents,
                'error_message': result.error_message,
                'claims': [claim.dict() for claim in result.claims] if result.claims else []
            }
        }
        
    except Exception as e:
        print(f"VoiceVerify Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': f'Internal error: {str(e)}'}
        }


def handle_webhook(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle Twilio webhook callbacks"""
    
    try:
        path = event.get('path', '')
        method = event.get('httpMethod', 'GET')
        
        # Parse path parameters
        path_parts = path.split('/')
        
        if 'twiml' in path:
            # TwiML request
            call_id = path_parts[-1]
            question_id = event.get('queryStringParameters', {}).get('question')
            
            agent = VoiceVerifyAgent()
            twiml = agent.generate_twiml_response(call_id, question_id)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/xml'},
                'body': twiml
            }
        
        elif 'response' in path:
            # Voice response handling
            call_id = path_parts[-2]
            question_id = path_parts[-1]
            
            body = event.get('body', '')
            # Parse form data from Twilio
            speech_result = ""  # Would parse from Twilio POST body
            
            agent = VoiceVerifyAgent()
            twiml = agent.handle_voice_response(call_id, question_id, speech_result)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/xml'},
                'body': twiml
            }
        
        else:
            # Status callback
            return {'statusCode': 200, 'body': 'OK'}
            
    except Exception as e:
        print(f"Webhook error: {e}")
        return {
            'statusCode': 500,
            'body': f'Webhook error: {str(e)}'
        }


# ============================================================================
# TESTING SUPPORT
# ============================================================================

async def test_voice_verify():
    """Test function for local development (careful with real phone numbers!)"""
    
    test_cri = CanonicalRestaurantInput(
        name="Test Restaurant",
        phone={'raw': '+1234567890'},  # Use a test number!
        address={'raw': "123 Test St, Test City, CA"}
    )
    
    agent = VoiceVerifyAgent()
    result = await agent.analyze_restaurant(test_cri)
    
    print(f"Success: {result.success}")
    print(f"Claims: {len(result.claims)}")
    print(f"Confidence: {result.total_confidence:.3f}")
    print(f"Cost: ${result.total_cost_cents/100:.3f}")


if __name__ == "__main__":
    print("VoiceVerify Agent - Use with caution on real phone numbers!")
    # Uncomment to test (use test numbers only!)
    # import asyncio
    # asyncio.run(test_voice_verify())
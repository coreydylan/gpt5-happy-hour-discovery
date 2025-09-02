"""
FastAPI Orchestrator - Central coordination service for happy hour discovery
This service manages the entire analysis pipeline, coordinating agents and consensus.

USES GPT-5 EXCLUSIVELY for all AI operations.
"""

import json
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import boto3
from supabase import create_client, Client
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import shared modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import (
    CanonicalRestaurantInput,
    AgentResult,
    AgentType,
    JobStatus
)
from shared.consensus import ConsensusEngine
from shared.gpt5_config import GPT5Config


# ============================================================================
# CONFIGURATION
# ============================================================================

class OrchestratorConfig:
    """Configuration for orchestrator service"""
    
    # Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')  # Use service key to bypass RLS
    
    # AWS
    SQS_QUEUE_PREFIX = os.environ.get('SQS_QUEUE_PREFIX', 'happy-hour-')
    LAMBDA_PREFIX = os.environ.get('LAMBDA_PREFIX', 'happy-hour-')
    
    # Agent timeouts (seconds)
    AGENT_TIMEOUTS = {
        AgentType.SITE_AGENT: 30,
        AgentType.GOOGLE_AGENT: 25,
        AgentType.YELP_AGENT: 20,
        AgentType.VOICE_VERIFY: 60  # Longer for phone calls
    }
    
    # Cost thresholds (cents)
    MAX_COST_PER_RESTAURANT = 50  # $0.50 max per restaurant
    CONFIDENCE_THRESHOLD_SKIP_EXPENSIVE = 0.8  # Skip VoiceVerify if confidence > 80%
    
    # Concurrency
    MAX_CONCURRENT_AGENTS = 3


# ============================================================================
# MODELS
# ============================================================================

class RestaurantLookupRequest(BaseModel):
    """Request to analyze a restaurant"""
    name: str = Field(..., description="Restaurant name")
    address: Optional[str] = Field(None, description="Restaurant address")
    phone: Optional[str] = Field(None, description="Restaurant phone")
    website: Optional[str] = Field(None, description="Restaurant website")
    
    # Control flags
    skip_voice_verify: bool = Field(False, description="Skip phone verification")
    priority: int = Field(5, description="Priority: 1 (highest) to 10 (lowest)")
    

class BulkUploadRequest(BaseModel):
    """Bulk upload of restaurants"""
    restaurants: List[RestaurantLookupRequest]
    skip_duplicates: bool = Field(True, description="Skip restaurants already in DB")


class JobStatusResponse(BaseModel):
    """Response for job status check"""
    job_id: str
    status: JobStatus
    venue_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    
    # Results
    confidence_score: Optional[float]
    happy_hour_found: Optional[bool]
    consensus_data: Optional[Dict[str, Any]]
    
    # Costs
    total_cost_cents: Optional[int]
    agents_completed: Optional[List[str]]
    
    # Errors
    error_message: Optional[str]


# ============================================================================
# ORCHESTRATOR SERVICE
# ============================================================================

class Orchestrator:
    """Main orchestration service"""
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        
        # Initialize clients
        self.supabase: Client = create_client(
            self.config.SUPABASE_URL,
            self.config.SUPABASE_KEY
        )
        self.sqs = boto3.client('sqs')
        self.lambda_client = boto3.client('lambda')
        
        # Consensus engine
        self.consensus_engine = ConsensusEngine()
        
        # Cost tracking
        self.total_cost_cents = 0
    
    async def analyze_restaurant(
        self, 
        request: RestaurantLookupRequest,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """
        Main entry point for restaurant analysis
        
        Args:
            request: Restaurant lookup request
            background_tasks: FastAPI background tasks
            
        Returns:
            Job information with ID for tracking
        """
        
        # Step 1: Create or find venue in database
        venue_id = await self._get_or_create_venue(request)
        
        # Step 2: Check for recent analysis
        recent_analysis = await self._check_recent_analysis(venue_id)
        if recent_analysis:
            return {
                'job_id': recent_analysis['id'],
                'venue_id': venue_id,
                'status': 'completed',
                'message': 'Using recent analysis from cache',
                'confidence_score': recent_analysis['confidence_score'],
                'happy_hour_found': recent_analysis['happy_hour_found']
            }
        
        # Step 3: Create analysis job
        job_id = str(uuid.uuid4())
        job_data = {
            'id': job_id,
            'venue_id': venue_id,
            'status': 'queued',  # Changed from 'pending' to match schema
            'source': 'api',
            'priority': request.priority,
            'started_at': datetime.utcnow().isoformat(),
            'cri': {
                'name': request.name,
                'address': request.address,
                'phone': request.phone,
                'website': request.website
            }
        }
        
        # Insert job into database
        self.supabase.table('analysis_jobs').insert(job_data).execute()
        
        # Step 4: Queue analysis in background
        background_tasks.add_task(self._run_analysis_pipeline, job_id, venue_id, request)
        
        return {
            'job_id': job_id,
            'venue_id': venue_id,
            'status': 'pending',
            'message': 'Analysis started',
            'estimated_time_seconds': 45
        }
    
    async def _run_analysis_pipeline(
        self, 
        job_id: str, 
        venue_id: str, 
        request: RestaurantLookupRequest
    ):
        """
        Run the full analysis pipeline
        
        This is our core orchestration logic that:
        1. Invokes agents in parallel
        2. Aggregates evidence
        3. Runs consensus algorithm
        4. Stores results
        """
        
        try:
            # Update job status
            self.supabase.table('analysis_jobs').update({
                'status': 'in_progress',
                'started_at': datetime.utcnow().isoformat()
            }).eq('id', job_id).execute()
            
            # Create CRI
            cri = CanonicalRestaurantInput(
                cri_id=job_id,
                name=request.name,
                address={'raw': request.address} if request.address else None,
                phone=request.phone,
                website=request.website
            )
            
            # Step 1: Run Tier 1 agents in parallel (cheap, fast)
            tier1_agents = [
                AgentType.GOOGLE_AGENT,
                AgentType.YELP_AGENT
            ]
            
            if cri.website:
                tier1_agents.append(AgentType.SITE_AGENT)
            
            tier1_results = await self._run_agents_parallel(tier1_agents, cri, job_id)
            
            # Step 2: Calculate initial confidence
            all_claims = []
            for result in tier1_results:
                if result and result.success:
                    all_claims.extend(result.claims)
            
            initial_confidence = self._calculate_confidence(all_claims)
            
            # Step 3: Decide if we need VoiceVerify (expensive but authoritative)
            should_call = (
                not request.skip_voice_verify and
                cri.phone and
                initial_confidence < self.config.CONFIDENCE_THRESHOLD_SKIP_EXPENSIVE
            )
            
            if should_call:
                # Run VoiceVerify agent
                voice_result = await self._invoke_agent(
                    AgentType.VOICE_VERIFY, 
                    cri, 
                    job_id
                )
                if voice_result and voice_result.success:
                    all_claims.extend(voice_result.claims)
            
            # Step 4: Run consensus algorithm
            consensus_result = self.consensus_engine.calculate_consensus(all_claims)
            
            # Step 5: Store results
            final_data = {
                'status': 'completed',
                'completed_at': datetime.utcnow().isoformat(),
                'confidence_score': consensus_result['overall_confidence'],
                'happy_hour_found': consensus_result['has_happy_hour'],
                'consensus_data': consensus_result,
                'total_cost_cents': self.total_cost_cents,
                'agents_used': [r.agent_type.value for r in tier1_results if r]
            }
            
            if should_call:
                final_data['agents_used'].append(AgentType.VOICE_VERIFY.value)
            
            # Update job
            self.supabase.table('analysis_jobs').update(final_data).eq('id', job_id).execute()
            
            # Store happy hour record if found
            if consensus_result['has_happy_hour']:
                await self._store_happy_hour_record(venue_id, consensus_result)
            
        except Exception as e:
            # Update job with error
            self.supabase.table('analysis_jobs').update({
                'status': 'failed',
                'completed_at': datetime.utcnow().isoformat(),
                'error_message': str(e)
            }).eq('id', job_id).execute()
            
            raise e
    
    async def _run_agents_parallel(
        self, 
        agent_types: List[AgentType], 
        cri: CanonicalRestaurantInput,
        job_id: str
    ) -> List[Optional[AgentResult]]:
        """Run multiple agents in parallel"""
        
        tasks = []
        for agent_type in agent_types:
            task = asyncio.create_task(self._invoke_agent(agent_type, cri, job_id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        clean_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Agent {agent_types[i]} failed: {result}")
                clean_results.append(None)
            else:
                clean_results.append(result)
        
        return clean_results
    
    async def _invoke_agent(
        self, 
        agent_type: AgentType, 
        cri: CanonicalRestaurantInput,
        job_id: str
    ) -> Optional[AgentResult]:
        """Invoke a single agent Lambda function"""
        
        try:
            function_name = f"{self.config.LAMBDA_PREFIX}{agent_type.value}"
            
            payload = {
                'cri': cri.dict(),
                'job_id': job_id,
                'venue_id': cri.cri_id
            }
            
            # Invoke Lambda
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse response
            result_data = json.loads(response['Payload'].read())
            
            if result_data.get('statusCode') == 200:
                body = result_data.get('body', {})
                
                # Track costs
                if 'cost_cents' in body:
                    self.total_cost_cents += body['cost_cents']
                
                # Create AgentResult
                return AgentResult(
                    agent_type=agent_type,
                    cri_id=cri.cri_id,
                    success=body.get('success', False),
                    claims=body.get('claims', []),
                    total_confidence=body.get('total_confidence', 0),
                    execution_time_ms=body.get('execution_time_ms', 0),
                    total_cost_cents=body.get('cost_cents', 0),
                    error_message=body.get('error_message')
                )
            
            return None
            
        except Exception as e:
            print(f"Error invoking {agent_type}: {e}")
            return None
    
    def _calculate_confidence(self, claims) -> float:
        """Calculate overall confidence from claims"""
        if not claims:
            return 0.0
        
        # Average confidence weighted by specificity
        total_weight = 0
        weighted_confidence = 0
        
        for claim in claims:
            weight = 1.0
            if claim.specificity == 'exact':
                weight = 1.2
            elif claim.specificity == 'vague':
                weight = 0.6
            
            weighted_confidence += claim.agent_confidence * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    async def _get_or_create_venue(self, request: RestaurantLookupRequest) -> str:
        """Get existing venue or create new one"""
        
        # Check for existing venue by name and address
        query = self.supabase.table('venues').select('*')
        query = query.eq('name', request.name)
        
        if request.address:
            query = query.eq('address', request.address)
        
        result = query.execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]['id']
        
        # Create new venue
        # Parse address to extract city and state
        city = None
        state = None
        if request.address:
            # Try to extract city and state from address like "1216 PROSPECT ST, LA JOLLA, CA 92037"
            parts = request.address.split(',')
            if len(parts) >= 2:
                city = parts[-2].strip() if len(parts) >= 3 else None
                if parts[-1].strip():
                    state_zip = parts[-1].strip().split()
                    if state_zip:
                        state = state_zip[0] if len(state_zip) > 0 else None
        
        venue_data = {
            'id': str(uuid.uuid4()),
            'name': request.name,
            'address': request.address,
            'city': city,
            'state': state,
            'phone_e164': request.phone,  # Fixed: use phone_e164 column name
            'website': request.website,
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.supabase.table('venues').insert(venue_data).execute()
        return venue_data['id']
    
    async def _check_recent_analysis(self, venue_id: str) -> Optional[Dict]:
        """Check for recent analysis (within 7 days)"""
        
        cutoff_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        
        result = self.supabase.table('analysis_jobs').select('*').eq(
            'venue_id', venue_id
        ).eq(
            'status', 'completed'
        ).gte(
            'completed_at', cutoff_date
        ).order(
            'completed_at', desc=True
        ).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        return None
    
    async def _store_happy_hour_record(self, venue_id: str, consensus_data: Dict):
        """Store the final happy hour record"""
        
        record = {
            'id': str(uuid.uuid4()),
            'venue_id': venue_id,
            'confidence_score': consensus_data['overall_confidence'],
            'schedule': consensus_data.get('schedule'),
            'specials': consensus_data.get('specials'),
            'conditions': consensus_data.get('conditions'),
            'last_verified': datetime.utcnow().isoformat(),
            'consensus_data': consensus_data
        }
        
        self.supabase.table('happy_hour_records').upsert(record).execute()
    
    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        """Get status of an analysis job"""
        
        result = self.supabase.table('analysis_jobs').select('*').eq(
            'id', job_id
        ).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = result.data[0]
        
        return JobStatusResponse(
            job_id=job['id'],
            status=job['status'],
            venue_id=job.get('venue_id'),
            started_at=job['started_at'],
            completed_at=job.get('completed_at'),
            confidence_score=job.get('confidence_score'),
            happy_hour_found=job.get('happy_hour_found'),
            consensus_data=job.get('consensus_data'),
            total_cost_cents=job.get('total_cost_cents'),
            agents_completed=job.get('agents_used', []),
            error_message=job.get('error_message')
        )


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Happy Hour Discovery Orchestrator",
    description="GPT-5 powered happy hour discovery system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = Orchestrator()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "happy-hour-orchestrator",
        "gpt5_enabled": True,
        "version": "1.0.0"
    }


@app.post("/api/analyze")
async def analyze_restaurant(
    request: RestaurantLookupRequest,
    background_tasks: BackgroundTasks
):
    """Analyze a single restaurant for happy hour information"""
    
    result = await orchestrator.analyze_restaurant(request, background_tasks)
    return result


@app.post("/api/bulk-upload")
async def bulk_upload(
    request: BulkUploadRequest,
    background_tasks: BackgroundTasks
):
    """Upload multiple restaurants for analysis"""
    
    jobs = []
    
    for restaurant in request.restaurants:
        try:
            job = await orchestrator.analyze_restaurant(restaurant, background_tasks)
            jobs.append(job)
        except Exception as e:
            jobs.append({
                'error': str(e),
                'restaurant': restaurant.name
            })
    
    return {
        'total_submitted': len(request.restaurants),
        'jobs_created': len([j for j in jobs if 'job_id' in j]),
        'jobs': jobs
    }


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of an analysis job"""
    
    status = await orchestrator.get_job_status(job_id)
    return status


@app.get("/api/venue/{venue_id}/happy-hour")
async def get_venue_happy_hour(venue_id: str):
    """Get happy hour information for a venue"""
    
    result = orchestrator.supabase.table('happy_hour_records').select('*').eq(
        'venue_id', venue_id
    ).order('last_verified', desc=True).limit(1).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=404, detail="No happy hour data found")
    
    return result.data[0]


@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    
    # Get counts
    venues = orchestrator.supabase.table('venues').select('count', count='exact').execute()
    jobs = orchestrator.supabase.table('analysis_jobs').select('count', count='exact').execute()
    happy_hours = orchestrator.supabase.table('happy_hour_records').select('count', count='exact').execute()
    
    return {
        'total_venues': venues.count if venues else 0,
        'total_jobs': jobs.count if jobs else 0,
        'happy_hours_found': happy_hours.count if happy_hours else 0,
        'gpt5_enabled': True
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
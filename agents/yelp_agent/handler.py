"""
YelpAgent Lambda Handler - Yelp Fusion API & Review Analysis  
Tier B source (weight: 0.5) - User-generated content with business data

This agent:
1. Uses Yelp Fusion API for business details
2. Analyzes Yelp reviews for happy hour mentions
3. Processes business photos for menu information
4. Extracts structured business data and hours
5. USES GPT-5 EXCLUSIVELY for all analysis
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, quote_plus
import hashlib

import boto3
import httpx
from bs4 import BeautifulSoup
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
    HAPPY_HOUR_EXTRACTION_SCHEMA
)


# ============================================================================
# CONFIGURATION
# ============================================================================

class YelpAgentConfig:
    """Configuration for Yelp data extraction"""
    
    # API settings
    FUSION_API_BASE = "https://api.yelp.com/v3"
    REQUEST_TIMEOUT = 30
    MAX_REVIEWS = 50         # Maximum reviews to analyze
    MAX_PHOTOS = 10          # Maximum photos to analyze
    
    # Search parameters
    SEARCH_RADIUS = 1000     # 1km search radius
    SEARCH_LIMIT = 5         # Max business results to consider
    
    # Headers for API requests
    def get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    # Headers for web scraping (if needed)
    SCRAPE_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    # Happy hour detection patterns
    HAPPY_HOUR_PATTERNS = [
        r'\bhappy\s+hour?\b',
        r'\bhh\b',
        r'\bdrink\s+special\b',
        r'\bhalf\s+off\b', 
        r'\b\$?\d+\s+off\b',
        r'\bdiscounted?\s+(drink|beer|wine|cocktail)s?\b',
        r'\bearly\s+bird\b',
        r'\btwilight\b',
        r'\bafter\s+work\b',
        r'\bcocktail\s+hour\b',
        r'\b\$\d+\s+(beer|wine|cocktail|drink)s?\b',
        r'\btwo\s+for\s+one\b',
        r'\b2\s+for\s+1\b'
    ]
    
    # Analysis temperature for consistent extraction
    ANALYSIS_TEMPERATURE = 0.1


# ============================================================================
# YELP AGENT CLASS
# ============================================================================

class YelpAgent:
    """Yelp data extraction agent for happy hour information"""
    
    def __init__(self, config: Optional[YelpAgentConfig] = None):
        self.config = config or YelpAgentConfig()
        self.gpt5_client = GPT5Client(api_key=os.environ['OPENAI_API_KEY'])
        self.yelp_api_key = os.environ.get('YELP_API_KEY')
        self.s3_client = boto3.client('s3')
        self.results_bucket = os.environ.get('RESULTS_BUCKET')
        
        # Performance tracking
        self.start_time = time.time()
        self.total_cost_cents = 0
        self.api_calls_made = 0
    
    async def analyze_restaurant(self, cri: CanonicalRestaurantInput) -> AgentResult:
        """
        Main analysis function: extract Yelp data for happy hour information
        
        Args:
            cri: Canonical Restaurant Input with location and details
            
        Returns:
            AgentResult with extracted claims and metadata
        """
        
        result = AgentResult(
            agent_type=AgentType.YELP_AGENT,
            cri_id=cri.cri_id,
            started_at=datetime.utcnow()
        )
        
        try:
            if not self.yelp_api_key:
                result.error_message = "No Yelp API key configured"
                result.success = False
                return result
            
            all_claims = []
            sources_accessed = []
            
            # Step 1: Find business using Fusion API
            business_data = None
            if cri.platform_ids and cri.platform_ids.yelp_business_id:
                # Direct lookup by business ID
                business_data = await self._get_business_by_id(cri.platform_ids.yelp_business_id)
                if business_data:
                    sources_accessed.append(f"Yelp API: {cri.platform_ids.yelp_business_id}")
            else:
                # Search for business
                business_id = await self._search_business(cri)
                if business_id:
                    business_data = await self._get_business_by_id(business_id)
                    sources_accessed.append(f"Yelp API: {business_id}")
            
            if not business_data:
                result.error_message = "Business not found on Yelp"
                result.success = False
                return result
            
            # Step 2: Extract basic business information
            business_claims = self._extract_business_data(business_data, cri)
            all_claims.extend(business_claims)
            
            # Step 3: Get and analyze reviews
            business_id = business_data.get('id')
            if business_id:
                reviews = await self._get_business_reviews(business_id)
                if reviews:
                    review_claims = await self._analyze_reviews(reviews, cri, business_data.get('url', ''))
                    all_claims.extend(review_claims)
            
            # Step 4: Analyze business photos for menu information
            photos = business_data.get('photos', [])
            if photos:
                photo_claims = await self._analyze_business_photos(photos, cri, business_data.get('url', ''))
                all_claims.extend(photo_claims)
            
            # Step 5: Calculate overall confidence
            total_confidence = self._calculate_agent_confidence(all_claims, business_data)
            
            # Success!
            result.claims = all_claims
            result.total_confidence = total_confidence
            result.success = True
            result.sources_accessed = sources_accessed
            result.completed_at = datetime.utcnow()
            result.execution_time_ms = int((time.time() - self.start_time) * 1000)
            result.total_cost_cents = self.total_cost_cents
            
            return result
            
        except Exception as e:
            result.error_message = f"YelpAgent failed: {str(e)}"
            result.success = False
            result.completed_at = datetime.utcnow()
            return result
    
    async def _search_business(self, cri: CanonicalRestaurantInput) -> Optional[str]:
        """
        Search for business using Yelp Fusion API
        
        Args:
            cri: Restaurant information for search
            
        Returns:
            Business ID if found
        """
        
        try:
            # Build search parameters
            params = {
                'term': cri.name,
                'limit': self.config.SEARCH_LIMIT,
                'radius': self.config.SEARCH_RADIUS,
                'categories': 'restaurants,bars'
            }
            
            # Add location if available
            if cri.address and cri.address.city:
                if cri.address.state:
                    params['location'] = f"{cri.address.city}, {cri.address.state}"
                else:
                    params['location'] = cri.address.city
            elif cri.coordinates:
                params['latitude'] = cri.coordinates.latitude
                params['longitude'] = cri.coordinates.longitude
            else:
                # Can't search without location
                return None
            
            headers = self.config.get_headers(self.yelp_api_key)
            
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT) as client:
                response = await client.get(
                    f"{self.config.FUSION_API_BASE}/businesses/search",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                self.api_calls_made += 1
                
                # Find best match
                businesses = data.get('businesses', [])
                for business in businesses:
                    if self._is_likely_match(business, cri):
                        return business.get('id')
                
                return None
                
        except Exception as e:
            print(f"Error searching Yelp: {e}")
            return None
    
    def _is_likely_match(self, business: Dict, cri: CanonicalRestaurantInput) -> bool:
        """Check if a Yelp business matches our restaurant"""
        
        business_name = business.get('name', '').lower()
        cri_name = cri.name.lower()
        
        # Name similarity check
        if not (cri_name in business_name or business_name in cri_name or self._names_similar(cri_name, business_name)):
            return False
        
        # Phone number check if available
        if cri.phone and cri.phone.e164 and business.get('display_phone'):
            business_phone = re.sub(r'[^\d+]', '', business['display_phone'])
            cri_phone = cri.phone.e164
            if business_phone != cri_phone:
                return False
        
        # Address check if available  
        if cri.address and cri.address.raw and business.get('location'):
            business_address = business['location'].get('display_address', [])
            business_address_str = ' '.join(business_address).lower()
            cri_address_str = cri.address.raw.lower()
            
            # Check if street numbers match (strong indicator)
            cri_street_num = re.search(r'^(\d+)', cri_address_str)
            business_street_num = re.search(r'^(\d+)', business_address_str)
            
            if cri_street_num and business_street_num:
                if cri_street_num.group(1) != business_street_num.group(1):
                    return False
        
        return True
    
    def _names_similar(self, name1: str, name2: str) -> bool:
        """Check similarity between restaurant names"""
        
        # Remove common words
        common_words = {'restaurant', 'bar', 'grill', 'cafe', 'bistro', 'the', 'and', 'at'}
        
        words1 = set(name1.split()) - common_words
        words2 = set(name2.split()) - common_words
        
        if not words1 or not words2:
            return False
        
        # Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) > 0.4
    
    async def _get_business_by_id(self, business_id: str) -> Optional[Dict]:
        """
        Get business details by ID using Yelp Fusion API
        
        Args:
            business_id: Yelp business ID
            
        Returns:
            Business details dictionary
        """
        
        try:
            headers = self.config.get_headers(self.yelp_api_key)
            
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT) as client:
                response = await client.get(
                    f"{self.config.FUSION_API_BASE}/businesses/{business_id}",
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                self.api_calls_made += 1
                return data
                
        except Exception as e:
            print(f"Error getting Yelp business details: {e}")
            return None
    
    async def _get_business_reviews(self, business_id: str) -> Optional[List[Dict]]:
        """
        Get business reviews using Yelp Fusion API
        
        Args:
            business_id: Yelp business ID
            
        Returns:
            List of review dictionaries
        """
        
        try:
            headers = self.config.get_headers(self.yelp_api_key)
            
            # Yelp API only returns 3 reviews, but we'll take what we can get
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT) as client:
                response = await client.get(
                    f"{self.config.FUSION_API_BASE}/businesses/{business_id}/reviews",
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                self.api_calls_made += 1
                return data.get('reviews', [])
                
        except Exception as e:
            print(f"Error getting Yelp reviews: {e}")
            return None
    
    def _extract_business_data(self, business_data: Dict, cri: CanonicalRestaurantInput) -> List[AgentClaim]:
        """Extract structured claims from Yelp business data"""
        
        claims = []
        
        try:
            # Extract basic business info for validation
            if business_data.get('name'):
                claim = AgentClaim(
                    agent_type=AgentType.YELP_AGENT,
                    source_type=SourceType.YELP_REVIEW,  # Business listing treated as review platform
                    source_url=business_data.get('url', ''),
                    source_domain='yelp.com',
                    field_path='name',
                    field_value=business_data['name'],
                    agent_confidence=0.9,
                    specificity=Specificity.EXACT,
                    modality=Modality.STRUCTURED_DATA,
                    observed_at=datetime.utcnow(),
                    raw_snippet=business_data['name'],
                    raw_data={'yelp_business_data': business_data}
                )
                claims.append(claim)
            
            # Extract hours (might contain happy hour info)
            hours = business_data.get('hours', [])
            if hours:
                for hour_info in hours:
                    if hour_info.get('is_open_now') is not None:
                        # Check open hours for any special mentions
                        open_hours = hour_info.get('open', [])
                        for day_hours in open_hours:
                            day = day_hours.get('day')  # 0=Monday, 6=Sunday
                            start = day_hours.get('start')
                            end = day_hours.get('end')
                            
                            if start and end:
                                # Convert day number to day name
                                day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                                day_name = day_names[day] if day < 7 else 'unknown'
                                
                                claim = AgentClaim(
                                    agent_type=AgentType.YELP_AGENT,
                                    source_type=SourceType.YELP_REVIEW,
                                    source_url=business_data.get('url', ''),
                                    source_domain='yelp.com',
                                    field_path=f'hours.{day_name}',
                                    field_value={'start': start, 'end': end},
                                    agent_confidence=0.8,
                                    specificity=Specificity.EXACT,
                                    modality=Modality.STRUCTURED_DATA,
                                    observed_at=datetime.utcnow(),
                                    raw_snippet=f"{day_name}: {start}-{end}",
                                    raw_data={'yelp_hours': hour_info}
                                )
                                claims.append(claim)
            
            # Extract price level
            if business_data.get('price'):
                price_range = business_data['price']  # '$', '$$', '$$$', '$$$$'
                claim = AgentClaim(
                    agent_type=AgentType.YELP_AGENT,
                    source_type=SourceType.YELP_REVIEW,
                    source_url=business_data.get('url', ''),
                    source_domain='yelp.com',
                    field_path='price_range',
                    field_value=price_range,
                    agent_confidence=0.85,
                    specificity=Specificity.EXACT,
                    modality=Modality.STRUCTURED_DATA,
                    observed_at=datetime.utcnow(),
                    raw_snippet=f"Price range: {price_range}",
                    raw_data={'yelp_business_data': business_data}
                )
                claims.append(claim)
                
        except Exception as e:
            print(f"Error extracting business data: {e}")
        
        return claims
    
    async def _analyze_reviews(self, reviews: List[Dict], cri: CanonicalRestaurantInput, business_url: str) -> List[AgentClaim]:
        """
        Analyze Yelp reviews for happy hour mentions
        
        Args:
            reviews: List of review objects
            cri: Restaurant context  
            business_url: Yelp business URL
            
        Returns:
            List of claims from review analysis
        """
        
        relevant_reviews = []
        
        # Filter reviews that mention happy hour
        for review in reviews:
            review_text = review.get('text', '')
            if any(re.search(pattern, review_text, re.IGNORECASE) for pattern in self.config.HAPPY_HOUR_PATTERNS):
                relevant_reviews.append(review)
        
        if not relevant_reviews:
            return []
        
        # Prepare reviews for analysis
        review_summaries = []
        for review in relevant_reviews:
            user_name = review.get('user', {}).get('name', 'Anonymous')
            rating = review.get('rating', 'unknown')
            time_created = review.get('time_created', '')
            text = review.get('text', '')
            
            review_summary = f"Review by {user_name} ({rating} stars, {time_created}): {text}"
            review_summaries.append(review_summary)
        
        # Analyze with GPT
        return await self._analyze_yelp_content(
            review_summaries, 
            business_url, 
            cri, 
            SourceType.YELP_REVIEW
        )
    
    async def _analyze_business_photos(self, photos: List[str], cri: CanonicalRestaurantInput, business_url: str) -> List[AgentClaim]:
        """
        Analyze business photos for menu information (OCR)
        
        Args:
            photos: List of photo URLs
            cri: Restaurant context
            business_url: Yelp business URL
            
        Returns:
            List of claims from photo analysis
        """
        
        # For MVP, we'll skip photo OCR analysis due to complexity
        # This would involve downloading images, running OCR, and analyzing text
        # Could be added in future versions
        
        print(f"Photo analysis skipped for MVP - found {len(photos)} photos")
        return []
    
    async def _analyze_yelp_content(
        self, 
        text_contents: List[str], 
        source_url: str, 
        cri: CanonicalRestaurantInput,
        source_type: SourceType = SourceType.YELP_REVIEW
    ) -> List[AgentClaim]:
        """
        Analyze Yelp content using GPT-5 for happy hour extraction
        
        Args:
            text_contents: List of text snippets (reviews, etc.)
            source_url: Source URL for provenance
            cri: Restaurant context
            source_type: Type of Yelp content
            
        Returns:
            List of extracted claims
        """
        
        if not text_contents:
            return []
        
        # Combine text - GPT-5 can handle much more
        combined_text = "\n\n".join(text_contents)
        max_chars = 15000  # GPT-5 can handle 272K tokens
        if len(combined_text) > max_chars:
            combined_text = combined_text[:max_chars] + "...[truncated]"
        
        extraction_prompt = f"""
Extract happy hour information from Yelp reviews and content.

Restaurant: {cri.name}
Address: {getattr(cri.address, 'raw', 'Unknown') if cri.address else 'Unknown'}

YELP CONTENT:
{combined_text}

Extract ALL happy hour mentions including:
- Schedule (days, times)
- Specials and pricing
- Location restrictions
- Any conditions mentioned

Be conservative - only extract clearly stated information.
User reviews may be outdated, so keep confidence moderate (0.5-0.7 range).
Only extract explicitly stated facts, not opinions or guesses.
"""

        try:
            # Use GPT-5 with structured outputs
            request = create_extraction_request(
                prompt=extraction_prompt,
                schema=HAPPY_HOUR_EXTRACTION_SCHEMA,
                reasoning_effort=ReasoningEffort.MINIMAL,  # Fast extraction
                model=GPT5Model.GPT5_NANO  # Cheapest option for simple extraction
            )
            
            response = await self.gpt5_client.create_completion(request)
            
            # Track costs
            self.total_cost_cents += response.cost_cents
            
            # Parse response - GPT-5 with structured outputs should return valid JSON
            try:
                response_data = json.loads(response.content)
                if 'extractions' in response_data:
                    extractions = response_data['extractions']
                else:
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
                    claim = AgentClaim(
                        agent_type=AgentType.YELP_AGENT,
                        source_type=source_type,
                        source_url=source_url,
                        source_domain='yelp.com',
                        field_path=extraction['field_path'],
                        field_value=extraction['field_value'],
                        agent_confidence=extraction['confidence'],
                        specificity=Specificity(extraction.get('specificity', 'approximate')),
                        modality=Modality.TEXT,
                        observed_at=datetime.utcnow() - timedelta(days=30),  # Reviews tend to be older
                        raw_snippet=extraction.get('supporting_snippet', ''),
                        raw_data={
                            'gpt5_model': response.model,
                            'reasoning_tokens': response.reasoning_tokens,
                            'cost_cents': response.cost_cents,
                            'original_content': text_contents[:2]  # First 2 for debugging
                        }
                    )
                    claims.append(claim)
                except (ValidationError, ValueError) as e:
                    print(f"Error creating Yelp claim: {e}")
                    continue
            
            return claims
            
        except Exception as e:
            print(f"Error analyzing Yelp content: {e}")
            return []
    
    def _calculate_agent_confidence(self, claims: List[AgentClaim], business_data: Dict) -> float:
        """Calculate overall agent confidence"""
        
        if not claims:
            return 0.0
        
        # Base confidence
        avg_confidence = sum(claim.agent_confidence for claim in claims) / len(claims)
        
        # Bonus for API data vs scraped data
        api_bonus = 0.1 if self.api_calls_made > 0 else 0.0
        
        # Bonus for high-rated business (more reliable reviews)
        rating = business_data.get('rating', 0)
        rating_bonus = 0.05 if rating >= 4.0 else 0.0
        
        # Bonus for multiple reviews
        review_count = sum(1 for claim in claims if claim.source_type == SourceType.YELP_REVIEW)
        review_bonus = min(0.1, review_count * 0.03)
        
        return min(1.0, avg_confidence + api_bonus + rating_bonus + review_bonus)


# ============================================================================
# LAMBDA HANDLER
# ============================================================================

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for YelpAgent
    
    Event format:
    {
        "cri": {<CanonicalRestaurantInput>},
        "job_id": "<uuid>",
        "venue_id": "<uuid>"
    }
    """
    
    try:
        # Parse input
        cri_data = event.get('cri')
        if not cri_data:
            return {
                'statusCode': 400,
                'body': {'error': 'Missing CRI data'}
            }
        
        # Create CRI object
        cri = CanonicalRestaurantInput(**cri_data)
        
        # Create agent and run analysis
        agent = YelpAgent()
        
        # Run async analysis
        import asyncio
        result = asyncio.run(agent.analyze_restaurant(cri))
        
        # Return result
        return {
            'statusCode': 200,
            'body': {
                'success': result.success,
                'agent_type': result.agent_type.value,
                'claims_count': len(result.claims),
                'total_confidence': result.total_confidence,
                'execution_time_ms': result.execution_time_ms,
                'cost_cents': result.total_cost_cents,
                'api_calls_made': agent.api_calls_made,
                'error_message': result.error_message,
                'claims': [claim.dict() for claim in result.claims] if result.claims else []
            }
        }
        
    except Exception as e:
        print(f"YelpAgent Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': f'Internal error: {str(e)}'}
        }


# ============================================================================
# TESTING SUPPORT
# ============================================================================

async def test_yelp_agent():
    """Test function for local development"""
    
    test_cri = CanonicalRestaurantInput(
        name="Duke's La Jolla",
        address={'raw': "1216 Prospect St, La Jolla, CA 92037"},
        platform_ids={'yelp_business_id': 'dukes-la-jolla'}  # Replace with real ID
    )
    
    agent = YelpAgent()
    result = await agent.analyze_restaurant(test_cri)
    
    print(f"Success: {result.success}")
    print(f"Claims found: {len(result.claims)}")
    print(f"Confidence: {result.total_confidence:.3f}")
    print(f"Cost: ${result.total_cost_cents/100:.3f}")
    print(f"API calls: {agent.api_calls_made}")
    
    for claim in result.claims[:3]:
        print(f"\nClaim: {claim.field_path}")
        print(f"Value: {claim.field_value}")
        print(f"Source: {claim.source_type}")
        print(f"Confidence: {claim.agent_confidence:.3f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_yelp_agent())
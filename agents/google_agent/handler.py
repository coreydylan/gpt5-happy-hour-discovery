"""
GoogleAgent Lambda Handler - Google Business Profile & Places API Data
Tier A/B source (weight: 0.85) - Owner-managed and user-generated content

This agent:
1. Uses Google Places API for business details
2. Scrapes Google Business Profile posts and Q&A
3. Analyzes Google reviews for happy hour mentions
4. Extracts menu links and structured data
5. USES GPT-5 EXCLUSIVELY for all text extraction
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
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

class GoogleAgentConfig:
    """Configuration for Google data extraction"""
    
    # API settings
    REQUEST_TIMEOUT = 30
    MAX_REVIEWS = 50         # Maximum reviews to analyze
    MAX_QA_ITEMS = 20        # Maximum Q&A items to process
    MAX_POSTS = 10           # Maximum business posts to analyze
    
    # Google Places API
    PLACES_BASE_URL = "https://maps.googleapis.com/maps/api/place"
    
    # Headers for web scraping
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    # Keywords for filtering relevant content
    HAPPY_HOUR_PATTERNS = [
        r'\bhappy\s+hour?\b',
        r'\bhh\b',
        r'\bdrink\s+special\b',
        r'\bhalf\s+off\b',
        r'\b\$?\d+\s+off\b',
        r'\bearly\s+bird\b',
        r'\btwilight\b',
        r'\bafter\s+work\b',
        r'\bcocktail\s+hour\b',
        r'\bsocial\s+hour\b'
    ]
    
    # Temperature for consistent extraction
    EXTRACTION_TEMPERATURE = 0.1


# ============================================================================
# GOOGLE AGENT CLASS  
# ============================================================================

class GoogleAgent:
    """Google data extraction agent for happy hour information"""
    
    def __init__(self, config: Optional[GoogleAgentConfig] = None):
        self.config = config or GoogleAgentConfig()
        self.gpt5_client = GPT5Client(api_key=os.environ['OPENAI_API_KEY'])
        self.google_api_key = os.environ.get('GOOGLE_PLACES_API_KEY')
        self.s3_client = boto3.client('s3')
        self.results_bucket = os.environ.get('RESULTS_BUCKET')
        
        # Performance tracking
        self.start_time = time.time()
        self.total_cost_cents = 0
        self.api_calls_made = 0
    
    async def analyze_restaurant(self, cri: CanonicalRestaurantInput) -> AgentResult:
        """
        Main analysis function: extract Google data for happy hour information
        
        Args:
            cri: Canonical Restaurant Input with location and details
            
        Returns:
            AgentResult with extracted claims and metadata
        """
        
        result = AgentResult(
            agent_type=AgentType.GOOGLE_AGENT,
            cri_id=cri.cri_id,
            started_at=datetime.utcnow()
        )
        
        try:
            all_claims = []
            sources_accessed = []
            
            # Step 1: Find place using Places API if we have a place_id
            place_details = None
            if cri.platform_ids and cri.platform_ids.google_place_id:
                place_details = await self._get_place_details(cri.platform_ids.google_place_id)
                if place_details:
                    sources_accessed.append(f"Places API: {cri.platform_ids.google_place_id}")
            else:
                # Search for place if no place_id
                place_id = await self._search_place(cri)
                if place_id:
                    place_details = await self._get_place_details(place_id)
                    sources_accessed.append(f"Places API: {place_id}")
            
            # Step 2: Extract structured data from Places API response
            if place_details:
                places_claims = self._extract_from_places_api(place_details, cri)
                all_claims.extend(places_claims)
            
            # Step 3: Scrape Google Business Profile page for posts and Q&A
            if place_details and place_details.get('url'):
                profile_claims = await self._scrape_business_profile(place_details['url'], cri)
                all_claims.extend(profile_claims)
                sources_accessed.append(place_details['url'])
            
            # Step 4: Analyze reviews for happy hour mentions
            if place_details and place_details.get('reviews'):
                review_claims = await self._analyze_reviews(place_details['reviews'], cri)
                all_claims.extend(review_claims)
            
            # Step 5: Calculate overall confidence
            total_confidence = self._calculate_agent_confidence(all_claims)
            
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
            result.error_message = f"GoogleAgent failed: {str(e)}"
            result.success = False
            result.completed_at = datetime.utcnow()
            return result
    
    async def _search_place(self, cri: CanonicalRestaurantInput) -> Optional[str]:
        """
        Search for a place using Google Places Text Search
        
        Args:
            cri: Restaurant information for search
            
        Returns:
            Google Place ID if found
        """
        
        if not self.google_api_key:
            print("No Google Places API key configured")
            return None
        
        # Build search query
        query_parts = [cri.name]
        if cri.address and cri.address.city:
            query_parts.append(cri.address.city)
        if cri.address and cri.address.state:
            query_parts.append(cri.address.state)
        
        query = ", ".join(query_parts)
        
        try:
            params = {
                'query': query,
                'type': 'restaurant',
                'key': self.google_api_key
            }
            
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT) as client:
                response = await client.get(
                    f"{self.config.PLACES_BASE_URL}/textsearch/json",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                self.api_calls_made += 1
                
                # Find best match
                if data.get('results'):
                    # Simple matching - could be enhanced with fuzzy matching
                    for place in data['results']:
                        if self._is_likely_match(place, cri):
                            return place.get('place_id')
                
                return None
                
        except Exception as e:
            print(f"Error searching for place: {e}")
            return None
    
    def _is_likely_match(self, place: Dict, cri: CanonicalRestaurantInput) -> bool:
        """Check if a Places API result matches our restaurant"""
        
        place_name = place.get('name', '').lower()
        cri_name = cri.name.lower()
        
        # Simple name matching - could be enhanced
        return (
            cri_name in place_name or 
            place_name in cri_name or
            self._names_similar(cri_name, place_name)
        )
    
    def _names_similar(self, name1: str, name2: str) -> bool:
        """Basic similarity check for restaurant names"""
        # Remove common words and compare
        common_words = {'restaurant', 'bar', 'grill', 'cafe', 'the', 'and'}
        
        words1 = set(name1.split()) - common_words
        words2 = set(name2.split()) - common_words
        
        if not words1 or not words2:
            return False
        
        # Check if they share significant words
        intersection = words1 & words2
        union = words1 | words2
        
        # Jaccard similarity > 0.5
        return len(intersection) / len(union) > 0.5
    
    async def _get_place_details(self, place_id: str) -> Optional[Dict]:
        """
        Get detailed information about a place using Places API
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Place details dictionary
        """
        
        if not self.google_api_key:
            return None
        
        try:
            params = {
                'place_id': place_id,
                'fields': 'name,formatted_address,formatted_phone_number,website,url,reviews,opening_hours,price_level,rating,user_ratings_total',
                'key': self.google_api_key
            }
            
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT) as client:
                response = await client.get(
                    f"{self.config.PLACES_BASE_URL}/details/json",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                self.api_calls_made += 1
                
                if data.get('status') == 'OK':
                    return data.get('result')
                
                return None
                
        except Exception as e:
            print(f"Error getting place details: {e}")
            return None
    
    def _extract_from_places_api(self, place_details: Dict, cri: CanonicalRestaurantInput) -> List[AgentClaim]:
        """Extract structured claims from Google Places API response"""
        
        claims = []
        
        try:
            # Extract opening hours (might include happy hour info)
            opening_hours = place_details.get('opening_hours', {})
            if opening_hours.get('weekday_text'):
                for day_info in opening_hours['weekday_text']:
                    if any(pattern in day_info.lower() for pattern in ['happy', 'special']):
                        # This could be happy hour info in opening hours
                        claim = AgentClaim(
                            agent_type=AgentType.GOOGLE_AGENT,
                            source_type=SourceType.GOOGLE_POST,  # Treat as owner-managed
                            source_url=place_details.get('url', ''),
                            source_domain='maps.google.com',
                            field_path='schedule.raw_hours',
                            field_value=day_info,
                            agent_confidence=0.7,
                            specificity=Specificity.APPROXIMATE,
                            modality=Modality.STRUCTURED_DATA,
                            observed_at=datetime.utcnow(),
                            raw_snippet=day_info,
                            raw_data={'places_api_response': place_details}
                        )
                        claims.append(claim)
            
            # Extract basic venue info for validation
            if place_details.get('name'):
                claim = AgentClaim(
                    agent_type=AgentType.GOOGLE_AGENT,
                    source_type=SourceType.GOOGLE_POST,
                    source_url=place_details.get('url', ''),
                    source_domain='maps.google.com',
                    field_path='name',
                    field_value=place_details['name'],
                    agent_confidence=0.95,
                    specificity=Specificity.EXACT,
                    modality=Modality.STRUCTURED_DATA,
                    observed_at=datetime.utcnow(),
                    raw_snippet=place_details['name'],
                    raw_data={'places_api_response': place_details}
                )
                claims.append(claim)
            
        except Exception as e:
            print(f"Error extracting from Places API: {e}")
        
        return claims
    
    async def _scrape_business_profile(self, google_url: str, cri: CanonicalRestaurantInput) -> List[AgentClaim]:
        """
        Scrape Google Business Profile page for posts, Q&A, and additional info
        
        Args:
            google_url: Google Business Profile URL
            cri: Restaurant context
            
        Returns:
            List of claims from business profile
        """
        
        try:
            async with httpx.AsyncClient(
                timeout=self.config.REQUEST_TIMEOUT,
                headers=self.config.HEADERS,
                follow_redirects=True
            ) as client:
                
                response = await client.get(google_url)
                response.raise_for_status()
                html_content = response.text
                
                # Store raw HTML for debugging
                if self.results_bucket:
                    await self._store_raw_content(google_url, html_content)
                
                # Extract text content
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Look for happy hour related content in various sections
                happy_hour_texts = []
                
                # Check for posts, Q&A, and other text content
                for element in soup.find_all(text=True):
                    text = element.strip()
                    if text and len(text) > 10:  # Ignore very short text
                        if any(re.search(pattern, text, re.IGNORECASE) for pattern in self.config.HAPPY_HOUR_PATTERNS):
                            happy_hour_texts.append(text)
                
                # If we found relevant content, analyze it with GPT
                if happy_hour_texts:
                    return await self._analyze_google_content(happy_hour_texts, google_url, cri)
                
                return []
                
        except Exception as e:
            print(f"Error scraping Google Business Profile: {e}")
            return []
    
    async def _analyze_reviews(self, reviews: List[Dict], cri: CanonicalRestaurantInput) -> List[AgentClaim]:
        """
        Analyze Google reviews for happy hour mentions
        
        Args:
            reviews: List of review objects from Places API
            cri: Restaurant context
            
        Returns:
            List of claims from review analysis
        """
        
        relevant_reviews = []
        
        # Filter reviews that mention happy hour
        for review in reviews[:self.config.MAX_REVIEWS]:
            review_text = review.get('text', '')
            if any(re.search(pattern, review_text, re.IGNORECASE) for pattern in self.config.HAPPY_HOUR_PATTERNS):
                relevant_reviews.append(review)
        
        if not relevant_reviews:
            return []
        
        # Analyze relevant reviews with GPT
        review_texts = []
        for review in relevant_reviews[:10]:  # Limit to prevent token overflow
            author = review.get('author_name', 'Anonymous')
            time_desc = review.get('relative_time_description', 'recently')
            rating = review.get('rating', 'unknown')
            text = review.get('text', '')
            
            review_summary = f"Review by {author} ({time_desc}, {rating} stars): {text[:300]}"
            review_texts.append(review_summary)
        
        return await self._analyze_google_content(review_texts, "Google Reviews", cri, SourceType.GOOGLE_REVIEW)
    
    async def _analyze_google_content(
        self, 
        text_contents: List[str], 
        source_url: str, 
        cri: CanonicalRestaurantInput,
        source_type: SourceType = SourceType.GOOGLE_POST
    ) -> List[AgentClaim]:
        """
        Analyze Google content using GPT-5 for happy hour extraction
        
        Args:
            text_contents: List of text snippets to analyze
            source_url: Source URL for provenance
            cri: Restaurant context
            source_type: Type of Google content
            
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
Extract happy hour information from Google Business Profile content.

Restaurant: {cri.name}
Address: {getattr(cri.address, 'raw', 'Unknown') if cri.address else 'Unknown'}

GOOGLE CONTENT:
{combined_text}

Extract ALL happy hour information including:
- Schedule (days, times)
- Drink and food specials with pricing
- Location restrictions
- Conditions and blackout dates

Only extract explicitly stated information from the content.
"""

        try:
            # Use GPT-5 with structured outputs
            request = create_extraction_request(
                prompt=extraction_prompt,
                schema=HAPPY_HOUR_EXTRACTION_SCHEMA,
                reasoning_effort=ReasoningEffort.MINIMAL,  # Fast extraction
                model=GPT5Model.GPT5_MINI  # Cost-effective for extraction
            )
            
            # Make the API call
            response = await self.gpt5_client.create_completion(request)
            
            # Track costs
            self.total_cost_cents += response.cost_cents
            
            # Parse the structured response
            try:
                extractions_data = json.loads(response.content)
                extractions = extractions_data.get('extractions', [])
            except json.JSONDecodeError:
                extractions = []
            
            # Convert to AgentClaim objects
            claims = []
            for extraction in extractions:
                try:
                    claim = AgentClaim(
                        agent_type=AgentType.GOOGLE_AGENT,
                        source_type=source_type,
                        source_url=source_url,
                        source_domain='google.com',
                        field_path=extraction['field_path'],
                        field_value=extraction['field_value'],
                        agent_confidence=extraction['confidence'],
                        specificity=Specificity(extraction.get('specificity', 'approximate')),
                        modality=Modality.TEXT,
                        observed_at=datetime.utcnow() - timedelta(days=7),  # Assume content is ~1 week old
                        raw_snippet=extraction.get('supporting_snippet', ''),
                        raw_data={
                            'gpt5_model': response.model,
                            'reasoning_tokens': response.reasoning_tokens,
                            'cost_cents': response.cost_cents,
                            'original_content': text_contents[:3]  # Store first 3 pieces for debugging
                        }
                    )
                    claims.append(claim)
                except (ValidationError, ValueError) as e:
                    print(f"Error creating Google claim: {e}")
                    continue
            
            return claims
            
        except Exception as e:
            print(f"Error analyzing Google content with GPT-5: {e}")
            return []
    
    async def _store_raw_content(self, url: str, content: str) -> None:
        """Store raw HTML content in S3 for debugging"""
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            key = f"google_agent/raw_html/{url_hash}.html"
            
            self.s3_client.put_object(
                Bucket=self.results_bucket,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType='text/html',
                Metadata={
                    'source_url': url,
                    'scraped_at': datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            print(f"Error storing raw content: {e}")
    
    def _calculate_agent_confidence(self, claims: List[AgentClaim]) -> float:
        """Calculate overall agent confidence based on claims and data sources"""
        if not claims:
            return 0.0
        
        # Base confidence from individual claims
        total_confidence = sum(claim.agent_confidence for claim in claims)
        avg_confidence = total_confidence / len(claims)
        
        # Bonus for API calls (more reliable than scraping)
        api_bonus = 0.1 if self.api_calls_made > 0 else 0.0
        
        # Bonus for multiple types of sources
        source_types = set(claim.source_type for claim in claims)
        diversity_bonus = len(source_types) * 0.05
        
        return min(1.0, avg_confidence + api_bonus + diversity_bonus)


# ============================================================================
# LAMBDA HANDLER
# ============================================================================

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for GoogleAgent
    
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
        agent = GoogleAgent()
        
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
        print(f"GoogleAgent Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': f'Internal error: {str(e)}'}
        }


# ============================================================================
# TESTING SUPPORT
# ============================================================================

async def test_google_agent():
    """Test function for local development"""
    
    # Test CRI with Google Place ID
    test_cri = CanonicalRestaurantInput(
        name="Duke's La Jolla",
        address={'raw': "1216 Prospect St, La Jolla, CA 92037"},
        platform_ids={'google_place_id': 'ChIJexampleplaceid'}  # Replace with real ID
    )
    
    agent = GoogleAgent()
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
    asyncio.run(test_google_agent())
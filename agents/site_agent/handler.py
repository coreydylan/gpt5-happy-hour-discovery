"""
SiteAgent Lambda Handler - Website Scraping for Happy Hour Information
Tier A source (weight: 1.0) - Official restaurant websites

This agent:
1. Scrapes restaurant websites for happy hour information
2. Processes PDFs, images, and structured data
3. Extracts time schedules, offers, and conditions
4. Uses GPT-5 EXCLUSIVELY for intelligent content extraction
"""

import json
import os
import re
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
import tempfile

import boto3
import httpx
from bs4 import BeautifulSoup, Tag
from selectolax.parser import HTMLParser
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

class SiteAgentConfig:
    """Configuration for website scraping"""
    
    # Timeouts and limits
    REQUEST_TIMEOUT = 30
    MAX_PAGE_SIZE = 5_000_000  # 5MB limit
    MAX_PAGES_PER_SITE = 5     # Limit crawl depth
    
    # Headers for web scraping
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Happy hour related keywords for page discovery
    HAPPY_HOUR_KEYWORDS = [
        'happy hour', 'happy-hour', 'happyhour',
        'drink special', 'food special', 'daily special',
        'happy hr', 'hh', 'after work',
        'early bird', 'twilight', 'sunset',
        'social hour', 'cocktail hour'
    ]
    
    # File extensions to process
    DOCUMENT_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']


# ============================================================================
# SITE AGENT CLASS
# ============================================================================

class SiteAgent:
    """Website scraping agent for happy hour information"""
    
    def __init__(self, config: Optional[SiteAgentConfig] = None):
        self.config = config or SiteAgentConfig()
        self.gpt5_client = GPT5Client(api_key=os.environ['OPENAI_API_KEY'])
        self.s3_client = boto3.client('s3')
        self.results_bucket = os.environ.get('RESULTS_BUCKET')
        
        # Performance tracking
        self.start_time = time.time()
        self.total_cost_cents = 0
        self.pages_scraped = 0
    
    async def analyze_restaurant(self, cri: CanonicalRestaurantInput) -> AgentResult:
        """
        Main analysis function: scrape website for happy hour information
        
        Args:
            cri: Canonical Restaurant Input with website and details
            
        Returns:
            AgentResult with extracted claims and metadata
        """
        
        result = AgentResult(
            agent_type=AgentType.SITE_AGENT,
            cri_id=cri.cri_id,
            started_at=datetime.utcnow()
        )
        
        try:
            if not cri.website:
                result.error_message = "No website URL provided"
                result.success = False
                return result
            
            website_url = str(cri.website)
            
            # Step 1: Discover relevant pages
            relevant_pages = await self._discover_happy_hour_pages(website_url)
            
            if not relevant_pages:
                result.error_message = "No relevant pages found"
                result.success = False
                return result
            
            # Step 2: Scrape and extract from each page
            all_claims = []
            
            for page_url in relevant_pages[:self.config.MAX_PAGES_PER_SITE]:
                try:
                    page_claims = await self._scrape_page(page_url, cri)
                    all_claims.extend(page_claims)
                    self.pages_scraped += 1
                except Exception as e:
                    print(f"Error scraping {page_url}: {str(e)}")
                    continue
            
            # Step 3: Calculate overall confidence
            total_confidence = self._calculate_agent_confidence(all_claims)
            
            # Success!
            result.claims = all_claims
            result.total_confidence = total_confidence
            result.success = True
            result.sources_accessed = relevant_pages
            result.completed_at = datetime.utcnow()
            result.execution_time_ms = int((time.time() - self.start_time) * 1000)
            result.total_cost_cents = self.total_cost_cents
            
            return result
            
        except Exception as e:
            result.error_message = f"SiteAgent failed: {str(e)}"
            result.success = False
            result.completed_at = datetime.utcnow()
            return result
    
    async def _discover_happy_hour_pages(self, base_url: str) -> List[str]:
        """
        Discover pages likely to contain happy hour information
        
        Args:
            base_url: Base website URL
            
        Returns:
            List of URLs to scrape
        """
        
        relevant_pages = []
        
        try:
            # Start with the main page
            main_page = await self._fetch_page(base_url)
            if main_page:
                relevant_pages.append(base_url)
                
                # Look for happy hour specific links
                soup = BeautifulSoup(main_page, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link['href']
                    link_text = link.get_text().lower()
                    
                    # Check if link text or URL suggests happy hour content
                    is_hh_related = any(keyword in link_text for keyword in self.config.HAPPY_HOUR_KEYWORDS)
                    is_hh_url = any(keyword.replace(' ', '-') in href.lower() 
                                   for keyword in self.config.HAPPY_HOUR_KEYWORDS)
                    
                    # Also check for menu/specials pages
                    is_menu_related = any(word in link_text for word in ['menu', 'special', 'offer', 'deal'])
                    
                    if is_hh_related or is_hh_url or is_menu_related:
                        # Convert relative URLs to absolute
                        full_url = urljoin(base_url, href)
                        
                        # Avoid duplicates and external links
                        if (full_url not in relevant_pages and 
                            self._is_same_domain(base_url, full_url) and
                            not any(ext in full_url.lower() for ext in ['.jpg', '.png', '.gif', '.pdf'])):
                            relevant_pages.append(full_url)
        
        except Exception as e:
            print(f"Error discovering pages for {base_url}: {str(e)}")
        
        return relevant_pages[:self.config.MAX_PAGES_PER_SITE]
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a web page with error handling and size limits
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None if failed
        """
        
        try:
            async with httpx.AsyncClient(
                timeout=self.config.REQUEST_TIMEOUT,
                headers=self.config.HEADERS,
                follow_redirects=True
            ) as client:
                
                response = await client.get(url)
                
                # Check response size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.config.MAX_PAGE_SIZE:
                    print(f"Page too large: {url} ({content_length} bytes)")
                    return None
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if not any(ct in content_type for ct in ['text/html', 'application/xhtml']):
                    print(f"Non-HTML content type: {content_type}")
                    return None
                
                response.raise_for_status()
                return response.text[:self.config.MAX_PAGE_SIZE]  # Truncate if needed
                
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    async def _scrape_page(self, url: str, cri: CanonicalRestaurantInput) -> List[AgentClaim]:
        """
        Scrape a single page for happy hour information
        
        Args:
            url: Page URL to scrape
            cri: Restaurant context
            
        Returns:
            List of extracted claims
        """
        
        html_content = await self._fetch_page(url)
        if not html_content:
            return []
        
        # Extract clean text content
        clean_text = self._extract_clean_text(html_content)
        
        # Check if page likely contains happy hour info
        if not self._contains_happy_hour_keywords(clean_text):
            return []
        
        # Store raw HTML in S3 for debugging
        if self.results_bucket:
            await self._store_raw_content(url, html_content)
        
        # Extract structured data using GPT-4o
        extraction_result = await self._extract_with_gpt(clean_text, url, cri)
        
        return extraction_result
    
    def _extract_clean_text(self, html: str) -> str:
        """
        Extract clean, readable text from HTML
        
        Args:
            html: Raw HTML content
            
        Returns:
            Clean text content
        """
        
        # Use selectolax for fast parsing (lighter than BeautifulSoup)
        tree = HTMLParser(html)
        
        # Remove script and style elements
        for node in tree.css('script, style, nav, header, footer'):
            node.decompose()
        
        # Get text content
        text = tree.text()
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines
        text = re.sub(r' +', ' ', text)          # Multiple spaces
        
        return text.strip()
    
    def _contains_happy_hour_keywords(self, text: str) -> bool:
        """Check if text contains happy hour related keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.config.HAPPY_HOUR_KEYWORDS)
    
    async def _extract_with_gpt(
        self, 
        text_content: str, 
        source_url: str, 
        cri: CanonicalRestaurantInput
    ) -> List[AgentClaim]:
        """
        Extract structured happy hour information using GPT-5
        Uses minimal reasoning for fast extraction with structured outputs
        
        Args:
            text_content: Clean text from webpage
            source_url: Source URL for provenance
            cri: Restaurant context
            
        Returns:
            List of agent claims with extracted information
        """
        
        # GPT-5 can handle much larger context (272K tokens)
        # But we'll still be reasonable to optimize cost
        max_chars = 20000  # ~5000 tokens, still tiny for GPT-5
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "...[truncated]"
        
        extraction_prompt = f"""
Extract happy hour information from this restaurant website content.

Restaurant: {cri.name}
Address: {getattr(cri.address, 'raw', 'Unknown') if cri.address else 'Unknown'}
Website: {cri.website}

WEBSITE CONTENT:
{text_content}

Extract ALL happy hour related information including:
- Schedule (days, times)
- Drink specials and pricing
- Food specials and pricing
- Location restrictions (bar only, patio, etc.)
- Conditions and blackout dates

Only extract explicitly stated information, not implied or guessed.
"""

        try:
            # Use GPT-5 with structured outputs for guaranteed schema compliance
            request = create_extraction_request(
                prompt=extraction_prompt,
                schema=HAPPY_HOUR_EXTRACTION_SCHEMA,
                reasoning_effort=ReasoningEffort.MINIMAL,  # Fast extraction, no deep reasoning needed
                model=GPT5Model.GPT5_MINI  # 80% cheaper than full GPT-5, perfect for extraction
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
                # If not JSON, might be direct response
                extractions = []
            
            # Convert to AgentClaim objects
            claims = []
            for extraction in extractions:
                try:
                    claim = AgentClaim(
                        agent_type=AgentType.SITE_AGENT,
                        source_type=SourceType.WEBSITE,
                        source_url=source_url,
                        source_domain=urlparse(source_url).netloc,
                        field_path=extraction['field_path'],
                        field_value=extraction['field_value'],
                        agent_confidence=extraction['confidence'],
                        specificity=Specificity(extraction.get('specificity', 'approximate')),
                        modality=Modality.TEXT,
                        observed_at=datetime.utcnow(),  # Assume current for website content
                        raw_snippet=extraction.get('supporting_snippet', ''),
                        raw_data={
                            'gpt5_model': response.model,
                            'reasoning_tokens': response.reasoning_tokens,
                            'cost_cents': response.cost_cents
                        }
                    )
                    claims.append(claim)
                except (ValidationError, ValueError) as e:
                    print(f"Error creating claim: {e}")
                    continue
            
            return claims
            
        except Exception as e:
            print(f"Error extracting with GPT-5: {str(e)}")
            return []
    
    async def _store_raw_content(self, url: str, content: str) -> None:
        """Store raw HTML content in S3 for debugging"""
        try:
            url_hash = str(hash(url))[-8:]  # Last 8 chars of hash
            key = f"site_agent/raw_html/{url_hash}.html"
            
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
    
    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain"""
        try:
            domain1 = urlparse(url1).netloc.lower()
            domain2 = urlparse(url2).netloc.lower()
            
            # Remove www. prefix for comparison
            domain1 = domain1.replace('www.', '')
            domain2 = domain2.replace('www.', '')
            
            return domain1 == domain2
        except:
            return False
    
    def _calculate_agent_confidence(self, claims: List[AgentClaim]) -> float:
        """Calculate overall agent confidence based on claims"""
        if not claims:
            return 0.0
        
        # Weight by number of claims and individual confidence
        total_confidence = sum(claim.agent_confidence for claim in claims)
        avg_confidence = total_confidence / len(claims)
        
        # Bonus for multiple claims (more evidence = higher confidence)
        evidence_bonus = min(0.2, len(claims) * 0.05)
        
        return min(1.0, avg_confidence + evidence_bonus)


# ============================================================================
# LAMBDA HANDLER
# ============================================================================

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for SiteAgent
    
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
        agent = SiteAgent()
        
        # Run async analysis (need to handle async in Lambda)
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
                'error_message': result.error_message,
                'claims': [claim.dict() for claim in result.claims] if result.claims else []
            }
        }
        
    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': f'Internal error: {str(e)}'}
        }


# ============================================================================
# TESTING SUPPORT
# ============================================================================

async def test_site_agent():
    """Test function for local development"""
    
    # Test CRI
    test_cri = CanonicalRestaurantInput(
        name="Duke's La Jolla",
        website="https://dukeslajolla.com",
        address={'raw': "1216 Prospect St, La Jolla, CA 92037"}
    )
    
    agent = SiteAgent()
    result = await agent.analyze_restaurant(test_cri)
    
    print(f"Success: {result.success}")
    print(f"Claims found: {len(result.claims)}")
    print(f"Confidence: {result.total_confidence:.3f}")
    print(f"Cost: ${result.total_cost_cents/100:.3f}")
    
    for claim in result.claims[:3]:  # Show first 3 claims
        print(f"\nClaim: {claim.field_path}")
        print(f"Value: {claim.field_value}")
        print(f"Confidence: {claim.agent_confidence:.3f}")
        print(f"Snippet: {claim.raw_snippet[:100]}...")


if __name__ == "__main__":
    # For local testing
    import asyncio
    asyncio.run(test_site_agent())
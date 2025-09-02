"""
Happy Hour Discovery System using GPT-5's Advanced Capabilities
Leverages parallel agent deployment, structured outputs, and deterministic JSON responses
"""

import asyncio
import json
import pandas as pd
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum
import aiohttp
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor
import hashlib
import time

# GPT-5 Model Configuration (Released August 2025)
# Available models: gpt-5, gpt-5-mini, gpt-5-nano
GPT5_MODEL = "gpt-5"  # Full capability model ($1.25/1M input, $10/1M output)
GPT5_THINKING_MODEL = "gpt-5"  # Uses reasoning_effort parameter for complex tasks
GPT5_CHAT_MODEL = "gpt-5-chat-latest"  # Non-reasoning chat model

class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class FoodCategory(str, Enum):
    APPETIZER = "appetizer"
    SMALL_PLATE = "small_plate"
    MAIN = "main"
    DESSERT = "dessert"
    SIDE = "side"
    SPECIAL = "special"

class DrinkCategory(str, Enum):
    BEER = "beer"
    WINE = "wine"
    COCKTAIL = "cocktail"
    SPIRIT = "spirit"
    NON_ALCOHOLIC = "non_alcoholic"
    SPECIAL = "special"

class PriceModifier(BaseModel):
    """Price modification during happy hour"""
    type: Literal["percentage_off", "fixed_price", "dollar_off", "bogo", "special"]
    value: Optional[float] = None
    description: Optional[str] = None

class MenuItem(BaseModel):
    """Individual menu item with happy hour pricing"""
    name: str
    regular_price: Optional[float] = None
    happy_hour_price: Optional[float] = None
    price_modifier: Optional[PriceModifier] = None
    description: Optional[str] = None
    restrictions: Optional[str] = None
    
class DrinkItem(MenuItem):
    """Drink-specific menu item"""
    category: DrinkCategory
    subcategory: Optional[str] = None  # e.g., "IPA", "Pinot Noir", "Margarita"
    size: Optional[str] = None
    abv: Optional[float] = None

class FoodItem(MenuItem):
    """Food-specific menu item"""
    category: FoodCategory
    dietary_tags: Optional[List[str]] = None  # vegetarian, vegan, gluten-free, etc.
    portion_size: Optional[str] = None

class TimeSlot(BaseModel):
    """Happy hour time slot"""
    start_time: str  # 24-hour format "15:00"
    end_time: str    # 24-hour format "19:00"
    description: Optional[str] = None  # "Early bird", "Late night", etc.

class DaySchedule(BaseModel):
    """Happy hour schedule for a specific day"""
    day: DayOfWeek
    time_slots: List[TimeSlot] = []
    is_available: bool = False
    special_events: Optional[str] = None  # "Trivia night", "Live music", etc.
    restrictions: Optional[str] = None  # "Bar only", "Patio only", etc.

class HappyHourMenu(BaseModel):
    """Complete happy hour menu"""
    drinks: List[DrinkItem] = []
    food: List[FoodItem] = []
    specials_description: Optional[str] = None
    menu_last_updated: Optional[str] = None
    menu_source_url: Optional[str] = None

class DataSource(BaseModel):
    """Source information for data verification"""
    url: str
    domain: str
    title: str
    date_accessed: str
    reliability_score: float = Field(ge=0, le=1)  # 0-1 confidence score
    content_snippet: Optional[str] = None
    is_official: bool = False  # True if restaurant's official site

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"
    CONFLICTING = "conflicting"
    NO_DATA = "no_data"
    NEEDS_HUMAN_REVIEW = "needs_human_review"

class SearchAttempt(BaseModel):
    """Record of a search attempt"""
    query: str
    timestamp: str
    results_found: int
    relevant_results: int
    search_engine: str

class HappyHourData(BaseModel):
    """Complete happy hour information for a restaurant"""
    # Restaurant identification
    restaurant_id: str
    restaurant_name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Happy hour availability
    has_happy_hour: Optional[bool] = None
    verification_status: VerificationStatus
    confidence_score: float = Field(ge=0, le=1)
    
    # Schedule
    schedule: List[DaySchedule] = []
    schedule_notes: Optional[str] = None  # "Seasonal changes", "Holiday exceptions"
    
    # Menu
    menu: Optional[HappyHourMenu] = None
    
    # Special features
    reservation_required: Optional[bool] = None
    indoor_seating: Optional[bool] = None
    outdoor_seating: Optional[bool] = None
    bar_seating_only: Optional[bool] = None
    
    # Data sources and verification
    sources: List[DataSource] = []
    search_attempts: List[SearchAttempt] = []
    
    # Quality indicators
    data_completeness_score: float = Field(ge=0, le=1)
    last_verified: str
    requires_human_review: bool = False
    human_review_reasons: List[str] = []
    
    # GPT-5 reasoning trace
    reasoning_trace: Optional[str] = None
    extraction_metadata: Dict[str, Any] = {}

class AgentTask(BaseModel):
    """Task definition for parallel agent deployment"""
    task_id: str
    task_type: Literal["web_search", "data_extraction", "verification", "menu_parsing", "schedule_parsing"]
    restaurant_info: Dict[str, str]
    priority: int = Field(ge=1, le=10)
    max_attempts: int = 3
    timeout_seconds: int = 30

class AgentResult(BaseModel):
    """Result from an agent task"""
    task_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    tokens_used: int

class HappyHourDiscoverySystem:
    """Main system for discovering and extracting happy hour information"""
    
    def __init__(self, openai_api_key: str, max_parallel_agents: int = 10):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.max_parallel_agents = max_parallel_agents
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=max_parallel_agents)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        self.executor.shutdown(wait=True)
    
    async def discover_happy_hour(self, restaurant: Dict[str, str]) -> HappyHourData:
        """
        Main entry point for discovering happy hour information for a restaurant.
        Deploys multiple GPT-5 agents in parallel to gather comprehensive data.
        """
        start_time = time.time()
        
        # Create parallel agent tasks
        tasks = self._create_agent_tasks(restaurant)
        
        # Deploy agents in parallel using GPT-5's parallel processing capabilities
        results = await self._deploy_parallel_agents(tasks)
        
        # Aggregate and validate results
        aggregated_data = await self._aggregate_results(results, restaurant)
        
        # Perform final verification and scoring
        final_data = await self._verify_and_score(aggregated_data)
        
        # Add execution metadata
        final_data.extraction_metadata = {
            "total_execution_time": time.time() - start_time,
            "agents_deployed": len(tasks),
            "gpt5_model_used": GPT5_MODEL,
            "parallel_execution": True,
            "timestamp": datetime.now().isoformat()
        }
        
        return final_data
    
    def _create_agent_tasks(self, restaurant: Dict[str, str]) -> List[AgentTask]:
        """Create parallel agent tasks for comprehensive data gathering"""
        restaurant_id = hashlib.md5(f"{restaurant['Record Name']}_{restaurant['Address']}".encode()).hexdigest()[:12]
        
        # Convert all values to strings to ensure compatibility
        restaurant_str = {k: str(v) if v is not None else '' for k, v in restaurant.items()}
        
        tasks = []
        
        # High-priority official website search
        tasks.append(AgentTask(
            task_id=f"{restaurant_id}_official",
            task_type="web_search",
            restaurant_info=restaurant_str,
            priority=10,
            max_attempts=3
        ))
        
        # Review sites search (parallel)
        for platform in ["yelp", "google", "tripadvisor", "opentable", "foursquare"]:
            tasks.append(AgentTask(
                task_id=f"{restaurant_id}_{platform}",
                task_type="web_search",
                restaurant_info={**restaurant_str, "platform": platform},
                priority=8,
                max_attempts=2
            ))
        
        # Social media search
        for platform in ["instagram", "facebook", "twitter"]:
            tasks.append(AgentTask(
                task_id=f"{restaurant_id}_social_{platform}",
                task_type="web_search",
                restaurant_info={**restaurant_str, "platform": platform},
                priority=6,
                max_attempts=2
            ))
        
        # Local publications and blogs
        tasks.append(AgentTask(
            task_id=f"{restaurant_id}_local_media",
            task_type="web_search",
            restaurant_info={**restaurant_str, "search_type": "local_publications"},
            priority=5,
            max_attempts=2
        ))
        
        return tasks
    
    async def _deploy_parallel_agents(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """Deploy multiple GPT-5 agents in parallel with structured outputs"""
        
        # Sort by priority
        tasks.sort(key=lambda x: x.priority, reverse=True)
        
        # Create batches for parallel execution
        results = []
        for i in range(0, len(tasks), self.max_parallel_agents):
            batch = tasks[i:i + self.max_parallel_agents]
            batch_results = await asyncio.gather(
                *[self._execute_agent_task(task) for task in batch],
                return_exceptions=True
            )
            
            for task, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results.append(AgentResult(
                        task_id=task.task_id,
                        success=False,
                        error=str(result),
                        execution_time=0,
                        tokens_used=0
                    ))
                else:
                    results.append(result)
        
        return results
    
    async def _execute_agent_task(self, task: AgentTask) -> AgentResult:
        """Execute a single agent task using GPT-5 with structured outputs"""
        start_time = time.time()
        
        try:
            # Construct the prompt based on task type
            prompt = self._construct_agent_prompt(task)
            
            # Use GPT-5's structured output capability with proper parameters
            response = await self.client.chat.completions.create(
                model=GPT5_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(task.task_type)},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_object"  # GPT-5 JSON mode
                },
                # GPT-5 only supports default temperature
                max_completion_tokens=4000,  # GPT-5 uses max_completion_tokens
                tools=self._get_agent_tools(task.task_type) if self._get_agent_tools(task.task_type) else None,
                tool_choice="auto" if self._get_agent_tools(task.task_type) else None,
                parallel_tool_calls=True if self._get_agent_tools(task.task_type) else None  # GPT-5 parallel execution
            )
            
            # Parse structured response
            result_data = json.loads(response.choices[0].message.content)
            
            return AgentResult(
                task_id=task.task_id,
                success=True,
                data=result_data,
                execution_time=time.time() - start_time,
                tokens_used=response.usage.total_tokens
            )
            
        except Exception as e:
            return AgentResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
                tokens_used=0
            )
    
    def _construct_agent_prompt(self, task: AgentTask) -> str:
        """Construct detailed prompt for agent based on task type"""
        restaurant = task.restaurant_info
        base_info = f"""
        Restaurant: {restaurant.get('Record Name', 'Unknown')}
        Address: {restaurant.get('Address', '')}, {restaurant.get('City', '')}, {restaurant.get('State', '')} {restaurant.get('Zip', '')}
        Phone: {restaurant.get('Permit Owner Business Phone', 'Unknown')}
        """
        
        if task.task_type == "web_search":
            platform = task.restaurant_info.get('platform', 'general')
            return f"""
            {base_info}
            
            Task: Search for happy hour information on {platform}.
            
            Required information to extract:
            1. Does this restaurant have a happy hour? (yes/no/uncertain)
            2. Days and times of happy hour (be specific for each day)
            3. Menu items and prices during happy hour
            4. Any restrictions or special conditions
            5. Source URL and reliability assessment
            6. Date information was last updated
            
            If found, extract ALL menu items with prices.
            Categorize drinks (beer/wine/cocktail) and food (appetizer/main).
            Note any special deals or promotions.
            
            Return structured data matching the schema.
            """
            
        elif task.task_type == "verification":
            return f"""
            {base_info}
            
            Task: Verify and cross-reference happy hour information from multiple sources.
            
            Compare information and identify:
            1. Consistent information across sources
            2. Conflicting information that needs resolution
            3. Missing information gaps
            4. Overall confidence score (0-1)
            5. Recommendations for human review if needed
            
            Apply critical analysis to determine most reliable information.
            """
        
        return base_info
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Get specialized system prompt for each agent type"""
        base = """You are a GPT-5 agent specialized in extracting structured happy hour information.
        You must return valid JSON matching the provided schema.
        Be thorough, accurate, and cite sources.
        Use web search and data extraction tools as needed.
        """
        
        specifics = {
            "web_search": "Focus on finding current, accurate happy hour details from web sources.",
            "data_extraction": "Extract and structure all relevant happy hour information.",
            "verification": "Cross-reference and verify information accuracy from multiple sources.",
            "menu_parsing": "Parse and categorize menu items with prices and descriptions.",
            "schedule_parsing": "Extract and normalize schedule information into structured format."
        }
        
        return base + "\n" + specifics.get(task_type, "")
    
    def _get_task_schema(self, task_type: str) -> Dict:
        """Get JSON schema for structured output based on task type"""
        # This would return the appropriate Pydantic model schema
        # converted to JSON Schema format for GPT-5's structured output
        
        if task_type in ["web_search", "data_extraction"]:
            return {
                "name": "happy_hour_extraction",
                "schema": HappyHourData.model_json_schema()
            }
        elif task_type == "verification":
            return {
                "name": "verification_result",
                "schema": {
                    "type": "object",
                    "properties": {
                        "verification_status": {"type": "string"},
                        "confidence_score": {"type": "number"},
                        "conflicts": {"type": "array"},
                        "recommendations": {"type": "array"}
                    }
                }
            }
        return {}
    
    def _get_agent_tools(self, task_type: str) -> List[Dict]:
        """Get available tools for agent based on task type"""
        tools = []
        
        # Web search tool (GPT-5 built-in capability)
        if task_type in ["web_search", "verification"]:
            tools.append({
                "type": "web_search",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "num_results": {"type": "integer", "default": 5}
                        }
                    }
                }
            })
        
        # Image analysis tool (for menu photos)
        if task_type in ["menu_parsing", "data_extraction"]:
            tools.append({
                "type": "image_analysis",
                "function": {
                    "name": "analyze_image",
                    "description": "Analyze images for text and content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_url": {"type": "string"}
                        }
                    }
                }
            })
        
        return tools
    
    async def _aggregate_results(self, results: List[AgentResult], restaurant: Dict) -> HappyHourData:
        """Aggregate results from multiple agents using GPT-5's reasoning capabilities"""
        
        # Filter successful results
        successful_results = [r for r in results if r.success and r.data]
        
        if not successful_results:
            return self._create_empty_result(restaurant, "no_data")
        
        # Use GPT-5 with high reasoning effort for complex aggregation
        aggregation_prompt = f"""
        Aggregate and reconcile the following {len(successful_results)} data sources about happy hour information.
        Resolve conflicts by preferring:
        1. Official website data
        2. More recent information
        3. More detailed information
        4. Consistent information across multiple sources
        
        Data sources:
        {json.dumps([r.data for r in successful_results], indent=2)}
        
        Produce a single, comprehensive, accurate dataset in JSON format matching the HappyHourData schema.
        Include all fields: restaurant_id, restaurant_name, address, has_happy_hour, verification_status, 
        confidence_score, schedule, menu, sources, data_completeness_score, last_verified, 
        requires_human_review, human_review_reasons.
        """
        
        response = await self.client.chat.completions.create(
            model=GPT5_THINKING_MODEL,  # GPT-5 with reasoning capability
            messages=[
                {"role": "system", "content": "You are an expert data aggregator. Reconcile multiple data sources into a single, accurate dataset. Return valid JSON."},
                {"role": "user", "content": aggregation_prompt}
            ],
            response_format={
                "type": "json_object"  # GPT-5 JSON mode
            }
            # GPT-5 uses default temperature
        )
        
        try:
            aggregated_dict = json.loads(response.choices[0].message.content)
            aggregated = HappyHourData.model_validate(aggregated_dict)
        except Exception as e:
            # Fallback if parsing fails
            aggregated = self._create_empty_result(restaurant, f"Aggregation error: {str(e)}")
        
        return aggregated
    
    async def _verify_and_score(self, data: HappyHourData) -> HappyHourData:
        """Final verification and scoring pass"""
        
        # Calculate data completeness score
        completeness_score = self._calculate_completeness(data)
        data.data_completeness_score = completeness_score
        
        # Determine if human review is needed
        if completeness_score < 0.6:
            data.requires_human_review = True
            data.human_review_reasons.append("Low data completeness")
        
        if data.verification_status in [VerificationStatus.CONFLICTING, VerificationStatus.UNCERTAIN]:
            data.requires_human_review = True
            data.human_review_reasons.append(f"Verification status: {data.verification_status}")
        
        if not data.sources or len(data.sources) < 2:
            data.requires_human_review = True
            data.human_review_reasons.append("Insufficient sources")
        
        # Set confidence score based on multiple factors
        confidence_factors = [
            completeness_score * 0.3,
            (len(data.sources) / 10) * 0.2,  # More sources = higher confidence
            (1.0 if data.verification_status == VerificationStatus.VERIFIED else 0.5) * 0.3,
            (1.0 if any(s.is_official for s in data.sources) else 0.7) * 0.2
        ]
        data.confidence_score = min(sum(confidence_factors), 1.0)
        
        data.last_verified = datetime.now().isoformat()
        
        return data
    
    def _calculate_completeness(self, data: HappyHourData) -> float:
        """Calculate how complete the data is"""
        scores = []
        
        # Check schedule completeness
        if data.schedule:
            days_covered = len([d for d in data.schedule if d.is_available])
            scores.append(days_covered / 7)
        else:
            scores.append(0)
        
        # Check menu completeness
        if data.menu:
            menu_score = 0
            if data.menu.drinks:
                menu_score += 0.5
            if data.menu.food:
                menu_score += 0.5
            scores.append(menu_score)
        else:
            scores.append(0)
        
        # Check basic info
        basic_fields = [
            data.has_happy_hour is not None,
            data.website is not None,
            data.phone is not None,
            bool(data.sources)
        ]
        scores.append(sum(basic_fields) / len(basic_fields))
        
        return sum(scores) / len(scores) if scores else 0
    
    def _create_empty_result(self, restaurant: Dict, reason: str) -> HappyHourData:
        """Create an empty result when no data is found"""
        return HappyHourData(
            restaurant_id=hashlib.md5(f"{restaurant['Record Name']}_{restaurant['Address']}".encode()).hexdigest()[:12],
            restaurant_name=restaurant.get('Record Name', 'Unknown'),
            address=restaurant.get('Address', ''),
            verification_status=VerificationStatus.NO_DATA,
            confidence_score=0,
            data_completeness_score=0,
            last_verified=datetime.now().isoformat(),
            requires_human_review=True,
            human_review_reasons=[reason]
        )

async def process_restaurants_batch(csv_file: str, output_file: str, api_key: str, batch_size: int = 5):
    """Process restaurants from CSV in batches"""
    
    # Read CSV
    df = pd.read_csv(csv_file)
    restaurants = df.to_dict('records')
    
    results = []
    
    async with HappyHourDiscoverySystem(api_key, max_parallel_agents=10) as system:
        # Process in batches
        for i in range(0, len(restaurants), batch_size):
            batch = restaurants[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} restaurants)...")
            
            # Process batch in parallel
            batch_results = await asyncio.gather(
                *[system.discover_happy_hour(r) for r in batch],
                return_exceptions=True
            )
            
            for restaurant, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    print(f"Error processing {restaurant['Record Name']}: {result}")
                    results.append({
                        "restaurant_name": restaurant['Record Name'],
                        "error": str(result),
                        "status": "failed"
                    })
                else:
                    results.append(result.model_dump())
                    print(f"Successfully processed {restaurant['Record Name']}")
                    print(f"  - Has Happy Hour: {result.has_happy_hour}")
                    print(f"  - Confidence: {result.confidence_score:.2f}")
                    print(f"  - Completeness: {result.data_completeness_score:.2f}")
                    if result.requires_human_review:
                        print(f"  - ⚠️ Requires human review: {', '.join(result.human_review_reasons)}")
            
            # Save intermediate results
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Rate limiting pause
            await asyncio.sleep(2)
    
    print(f"\nProcessing complete! Results saved to {output_file}")
    print(f"Total processed: {len(results)}")
    print(f"Requiring review: {sum(1 for r in results if r.get('requires_human_review', False))}")
    
    return results

# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configuration
    API_KEY = os.getenv("OPENAI_API_KEY")
    CSV_FILE = "food_permits_restaurants.csv"
    OUTPUT_FILE = "happy_hour_results.json"
    
    # Run the discovery system
    asyncio.run(process_restaurants_batch(
        csv_file=CSV_FILE,
        output_file=OUTPUT_FILE,
        api_key=API_KEY,
        batch_size=3  # Process 3 restaurants at a time
    ))
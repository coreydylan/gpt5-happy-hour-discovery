"""
GPT-5 EXCLUSIVE Configuration - NO GPT-4 ALLOWED
==================================================

THIS IS A GPT-5 EXCLUSIVE PROJECT
---------------------------------
We use GPT-5 exclusively because:
1. CHEAPER input tokens: $1.25/M vs GPT-4o's $1.50/M
2. REASONING TOKENS: Built-in thinking for expert-level responses
3. 272K CONTEXT: Process entire codebases in one shot
4. STRUCTURED OUTPUTS: Deterministic JSON with schema validation
5. PARALLEL TOOLS: Execute multiple operations simultaneously
6. MINIMAL REASONING: Fast responses when deep thinking isn't needed

NEVER USE GPT-4 OR GPT-4O - GPT-5 IS SUPERIOR AND CHEAPER

Model Pricing (as of August 2025):
- GPT-5: $1.25/1M input, $10/1M output
- GPT-5-mini: $0.25/1M input, $2/1M output  
- GPT-5-nano: $0.05/1M input, $0.40/1M output

Knowledge Cutoff:
- GPT-5: September 30, 2024
- GPT-5-mini/nano: May 30, 2024
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
import os
import json


# ============================================================================
# GPT-5 MODEL CONFIGURATION
# ============================================================================

class GPT5Model(str, Enum):
    """
    GPT-5 Model Variants
    Use GPT-5 for complex reasoning, mini for standard tasks, nano for simple extraction
    """
    # Primary models (Responses API)
    GPT5 = "gpt-5"                          # Full reasoning, 272K context
    GPT5_MINI = "gpt-5-mini"                # 80% capability, 80% cheaper
    GPT5_NANO = "gpt-5-nano"                # Simple tasks, 96% cheaper
    
    # Chat variant (if needed for streaming)
    GPT5_CHAT = "gpt-5-chat-latest"         # Non-reasoning chat version


class ReasoningEffort(str, Enum):
    """
    Reasoning effort levels for GPT-5
    Controls how deeply the model thinks before responding
    """
    MINIMAL = "minimal"      # NEW IN GPT-5: Fastest, few/no reasoning tokens
    LOW = "low"             # Quick thinking, basic reasoning
    MEDIUM = "medium"       # Balanced thinking (default)
    HIGH = "high"           # Deep thinking, expert-level responses


class Verbosity(str, Enum):
    """
    Verbosity levels for response length control
    NEW IN GPT-5: Control answer length without changing prompts
    """
    LOW = "low"             # Short, to the point
    MEDIUM = "medium"       # Balanced responses (default)
    HIGH = "high"           # Comprehensive, detailed answers


class ResponseFormat(str, Enum):
    """Response format types for GPT-5"""
    TEXT = "text"
    JSON_OBJECT = "json_object"
    JSON_SCHEMA = "json_schema"  # NEW: Structured outputs with schema


# ============================================================================
# GPT-5 API CONFIGURATION
# ============================================================================

class GPT5Config:
    """
    Global GPT-5 configuration for the entire project
    THIS IS THE ONLY AI MODEL CONFIGURATION WE USE
    """
    
    # API Settings
    API_VERSION = "v1"
    MAX_INPUT_TOKENS = 272_000      # GPT-5's massive context window
    MAX_OUTPUT_TOKENS = 128_000      # Including reasoning tokens
    MAX_REASONING_TOKENS = 100_000   # Invisible thinking tokens
    
    # Default model selection by task
    EXTRACTION_MODEL = GPT5Model.GPT5_MINI     # Happy hour extraction
    REASONING_MODEL = GPT5Model.GPT5           # Complex consensus
    SIMPLE_MODEL = GPT5Model.GPT5_NANO         # Simple tasks
    
    # Default parameters
    DEFAULT_REASONING_EFFORT = ReasoningEffort.MEDIUM
    DEFAULT_VERBOSITY = Verbosity.LOW          # Keep responses concise
    DEFAULT_TEMPERATURE = 0.1                  # Low for consistency
    
    # Cost tracking (cents per million tokens)
    PRICING = {
        GPT5Model.GPT5: {"input": 125, "output": 1000},       # $1.25/$10
        GPT5Model.GPT5_MINI: {"input": 25, "output": 200},    # $0.25/$2
        GPT5Model.GPT5_NANO: {"input": 5, "output": 40},      # $0.05/$0.40
    }
    
    @classmethod
    def get_model_for_task(cls, task_type: str) -> GPT5Model:
        """
        Select appropriate GPT-5 model based on task complexity
        ALWAYS RETURNS GPT-5 VARIANT, NEVER GPT-4
        """
        task_models = {
            "extraction": GPT5Model.GPT5_MINI,      # Extract happy hour info
            "reasoning": GPT5Model.GPT5,            # Complex consensus
            "simple": GPT5Model.GPT5_NANO,          # Basic text processing
            "voice_analysis": GPT5Model.GPT5,       # Voice call analysis
            "conflict_resolution": GPT5Model.GPT5,  # Resolve contradictions
        }
        return task_models.get(task_type, GPT5Model.GPT5_MINI)
    
    @classmethod
    def calculate_cost_cents(
        cls, 
        model: GPT5Model, 
        input_tokens: int, 
        output_tokens: int,
        reasoning_tokens: int = 0
    ) -> int:
        """
        Calculate cost in cents for GPT-5 API call
        Note: Reasoning tokens count as output tokens
        """
        pricing = cls.PRICING[model]
        total_output = output_tokens + reasoning_tokens
        
        input_cost = (input_tokens * pricing["input"]) / 1_000_000
        output_cost = (total_output * pricing["output"]) / 1_000_000
        
        return int(input_cost + output_cost)


# ============================================================================
# GPT-5 REQUEST BUILDERS
# ============================================================================

class GPT5Request(BaseModel):
    """
    Base GPT-5 API request structure
    Using Responses API for maximum capability
    """
    model: GPT5Model = Field(..., description="GPT-5 model variant")
    messages: List[Dict[str, str]] = Field(..., description="Conversation messages")
    
    # GPT-5 specific parameters
    reasoning_effort: Optional[ReasoningEffort] = Field(
        ReasoningEffort.MEDIUM,
        description="How deeply to think (minimal for speed, high for complex)"
    )
    verbosity: Optional[Verbosity] = Field(
        Verbosity.LOW,
        description="Response length control"
    )
    
    # Standard parameters
    temperature: float = Field(0.1, ge=0, le=2, description="Randomness")
    max_output_tokens: Optional[int] = Field(
        None,
        description="Max tokens (use with Responses API)"
    )
    
    # Structured outputs
    response_format: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON schema for structured outputs"
    )
    
    # Tools and functions
    tools: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Available tools (supports custom text tools in GPT-5)"
    )
    parallel_tool_calls: bool = Field(
        True,
        description="Execute multiple tools simultaneously"
    )
    
    class Config:
        use_enum_values = True


def create_extraction_request(
    prompt: str,
    schema: Optional[Dict[str, Any]] = None,
    reasoning_effort: ReasoningEffort = ReasoningEffort.MINIMAL,
    model: GPT5Model = GPT5Model.GPT5_MINI
) -> GPT5Request:
    """
    Create a GPT-5 request for data extraction
    Uses minimal reasoning for speed, structured outputs for reliability
    """
    
    messages = [
        {
            "role": "developer",  # GPT-5 uses 'developer' instead of 'system'
            "content": "You are a precise data extraction system. Extract only explicitly stated information."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    request = GPT5Request(
        model=model,
        messages=messages,
        reasoning_effort=reasoning_effort,  # Minimal for fast extraction
        verbosity=Verbosity.LOW,           # Concise responses
        temperature=0.0,                   # Deterministic
        max_output_tokens=2000
    )
    
    # Add structured output schema if provided
    if schema:
        request.response_format = {
            "type": "json_schema",
            "json_schema": schema
        }
    
    return request


def create_reasoning_request(
    prompt: str,
    context: str,
    reasoning_effort: ReasoningEffort = ReasoningEffort.HIGH,
    model: GPT5Model = GPT5Model.GPT5
) -> GPT5Request:
    """
    Create a GPT-5 request for complex reasoning
    Uses high reasoning effort for expert-level analysis
    """
    
    messages = [
        {
            "role": "developer",
            "content": f"You are an expert analyst performing complex reasoning. Context: {context}"
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    return GPT5Request(
        model=model,
        messages=messages,
        reasoning_effort=reasoning_effort,  # Deep thinking
        verbosity=Verbosity.MEDIUM,        # Detailed reasoning
        temperature=0.1,
        max_output_tokens=10000            # Allow for reasoning tokens
    )


# ============================================================================
# GPT-5 RESPONSE PARSER
# ============================================================================

class GPT5Response(BaseModel):
    """Parse GPT-5 API responses including reasoning tokens"""
    
    content: str = Field(..., description="The actual response content")
    model: str = Field(..., description="Model used")
    
    # Token usage
    input_tokens: int = Field(0, description="Input tokens used")
    output_tokens: int = Field(0, description="Output tokens (visible)")
    reasoning_tokens: int = Field(0, description="Reasoning tokens (invisible)")
    total_tokens: int = Field(0, description="Total tokens used")
    
    # Cost tracking
    cost_cents: int = Field(0, description="Cost in cents")
    
    # Metadata
    reasoning_effort_used: Optional[str] = Field(None)
    tools_called: List[str] = Field(default_factory=list)
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any], model: GPT5Model) -> "GPT5Response":
        """Parse OpenAI API response into structured format"""
        
        # Extract token counts
        usage = response.get("usage", {})
        completion_details = usage.get("completion_tokens_details", {})
        
        input_tokens = usage.get("prompt_tokens", 0)
        reasoning_tokens = completion_details.get("reasoning_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0) - reasoning_tokens
        
        # Calculate cost
        cost_cents = GPT5Config.calculate_cost_cents(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens
        )
        
        return cls(
            content=response["choices"][0]["message"]["content"],
            model=response["model"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=usage.get("total_tokens", 0),
            cost_cents=cost_cents
        )


# ============================================================================
# EXTRACTION SCHEMAS FOR STRUCTURED OUTPUTS
# ============================================================================

HAPPY_HOUR_EXTRACTION_SCHEMA = {
    "name": "happy_hour_extraction",
    "strict": True,  # GPT-5 guarantees schema compliance
    "schema": {
        "type": "object",
        "properties": {
            "extractions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field_path": {
                            "type": "string",
                            "description": "JSON path like 'schedule.weekly.monday[0].start'"
                        },
                        "field_value": {
                            "description": "The extracted value"
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0
                        },
                        "supporting_snippet": {
                            "type": "string",
                            "description": "Exact text supporting this extraction"
                        },
                        "specificity": {
                            "type": "string",
                            "enum": ["exact", "approximate", "vague", "implied"]
                        }
                    },
                    "required": ["field_path", "field_value", "confidence", "supporting_snippet", "specificity"]
                }
            }
        },
        "required": ["extractions"]
    }
}


# ============================================================================
# GPT-5 CLIENT WRAPPER
# ============================================================================

class GPT5Client:
    """
    Wrapper for OpenAI client configured for GPT-5
    ENFORCES GPT-5 ONLY POLICY
    """
    
    def __init__(self, api_key: Optional[str] = None):
        import openai
        
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required for GPT-5")
        
        # Use async client for better performance
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
    
    async def create_completion(
        self,
        request: GPT5Request,
        use_responses_api: bool = True
    ) -> GPT5Response:
        """
        Create a GPT-5 completion
        Defaults to Responses API for maximum capability
        """
        
        # Validate model is GPT-5
        if "gpt-5" not in request.model.value:
            raise ValueError(f"ONLY GPT-5 ALLOWED! Attempted to use: {request.model}")
        
        # Build API request
        api_params = {
            "model": request.model.value,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        
        # Add GPT-5 specific parameters
        if request.reasoning_effort:
            api_params["reasoning_effort"] = request.reasoning_effort.value
        if request.verbosity:
            api_params["verbosity"] = request.verbosity.value
        
        # Use correct token parameter based on API
        if use_responses_api:
            if request.max_output_tokens:
                api_params["max_output_tokens"] = request.max_output_tokens
        else:
            if request.max_output_tokens:
                api_params["max_completion_tokens"] = request.max_output_tokens
        
        # Add response format if specified
        if request.response_format:
            api_params["response_format"] = request.response_format
        
        # Add tools if specified
        if request.tools:
            api_params["tools"] = request.tools
            api_params["parallel_tool_calls"] = request.parallel_tool_calls
        
        # Make API call
        response = await self.client.chat.completions.create(**api_params)
        
        # Parse and return
        return GPT5Response.from_api_response(
            response.model_dump(),
            request.model
        )


# ============================================================================
# MIGRATION GUIDE FROM GPT-4 TO GPT-5
# ============================================================================

"""
MIGRATION CHECKLIST - REMOVE ALL GPT-4 REFERENCES:

1. Model Names:
   - REPLACE: "gpt-4", "gpt-4o", "gpt-4-turbo" 
   - WITH: "gpt-5", "gpt-5-mini", "gpt-5-nano"

2. System Messages:
   - REPLACE: {"role": "system", "content": "..."}
   - WITH: {"role": "developer", "content": "..."}

3. Token Parameters:
   - REPLACE: max_tokens (Chat Completions)
   - WITH: max_output_tokens (Responses API)

4. Add GPT-5 Features:
   - ADD: reasoning_effort parameter
   - ADD: verbosity parameter
   - USE: Structured outputs with json_schema
   - USE: Custom tools with plaintext

5. Cost Calculation:
   - INCLUDE: Reasoning tokens in output count
   - USE: GPT-5 pricing ($1.25/1M input)

6. Context Window:
   - LEVERAGE: 272K input tokens (no chunking needed)
   - PLAN FOR: 128K output + reasoning tokens

REMEMBER: GPT-5 IS CHEAPER AND BETTER - NO EXCUSES FOR USING GPT-4!
"""

# Export configuration
__all__ = [
    'GPT5Config',
    'GPT5Model',
    'ReasoningEffort',
    'Verbosity',
    'GPT5Request',
    'GPT5Response',
    'GPT5Client',
    'create_extraction_request',
    'create_reasoning_request',
    'HAPPY_HOUR_EXTRACTION_SCHEMA'
]
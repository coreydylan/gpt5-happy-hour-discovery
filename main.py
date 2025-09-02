"""
GPT-5 Happy Hour Discovery System - FastAPI Orchestrator
Coordinates multiple AI agents to analyze restaurant happy hour information
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import boto3
from boto3.dynamodb.conditions import Attr
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GPT-5 Happy Hour Orchestrator", version="1.0.0")

# Create a sub-application for the /hhmap path
hhmap_app = FastAPI(title="GPT-5 Happy Hour Orchestrator", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class AnalysisRequest(BaseModel):
    restaurant_name: str
    address: str
    phone: Optional[str] = None
    business_type: Optional[str] = "restaurant"

class AnalysisResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    created_at: str
    completed_at: Optional[str] = None

# In-memory job storage (in production, use Redis or database)
jobs = {}

# GPT-5 Analysis Function
async def analyze_restaurant_with_gpt5(restaurant_name: str, address: str, phone: Optional[str] = None) -> Dict[str, Any]:
    """Analyze restaurant happy hour using GPT-5"""
    try:
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Construct comprehensive prompt
        prompt = f"""
        Find comprehensive happy hour information for this restaurant:
        
        Restaurant: {restaurant_name}
        Address: {address}
        {f"Phone: {phone}" if phone else ""}
        
        Search for and provide:
        1. Happy hour schedule (specific days and times)
        2. Drink specials and prices
        3. Food specials and prices
        4. Any restrictions or special conditions
        5. Location information (bar area, patio, etc.)
        
        Return as structured JSON with:
        - status: "active" | "inactive" | "unknown"
        - schedule: object with days as keys, times as arrays
        - offers: array of offer objects with type and description
        - areas: array of areas where happy hour is available
        - fine_print: array of restrictions or notes
        - confidence_score: 0-1 rating
        - evidence_count: number of sources found
        - source_diversity: description of source types
        
        If no happy hour found, return status: "inactive" with explanation.
        """
        
        # Call GPT-5 with appropriate token limits
        response = await client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a restaurant information specialist. Search for and extract happy hour information. Return valid JSON with structured data."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=4000  # Increased to account for reasoning tokens
        )
        
        # Parse GPT-5 response
        content = response.choices[0].message.content
        if not content or content.strip() == "":
            raise ValueError(f"GPT-5 returned empty content. Finish reason: {response.choices[0].finish_reason}")
        
        gpt5_result = json.loads(content)
        
        # Structure the response for our system
        return {
            "restaurant_name": restaurant_name,
            "address": address,
            "happy_hour_data": gpt5_result,
            "confidence_score": gpt5_result.get("confidence_score", 0.5),
            "evidence_count": gpt5_result.get("evidence_count", "Unknown"),
            "source_diversity": gpt5_result.get("source_diversity", "Unknown"),
            "gpt5_analysis": True,
            "model_used": "gpt-5",
            "tokens_used": response.usage.total_tokens,
            "analysis_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"GPT-5 analysis failed for {restaurant_name}: {str(e)}")
        # Return fallback data if GPT-5 fails
        return {
            "restaurant_name": restaurant_name,
            "address": address,
            "happy_hour_data": {
                "status": "unknown",
                "error": f"Analysis failed: {str(e)}",
                "schedule": {},
                "offers": [],
                "areas": [],
                "fine_print": ["Analysis temporarily unavailable"]
            },
            "confidence_score": 0.0,
            "evidence_count": 0,
            "source_diversity": "None",
            "gpt5_analysis": False,
            "model_used": "fallback",
            "tokens_used": 0,
            "analysis_time": datetime.now().isoformat()
        }

async def process_analysis_job(job_id: str, request: AnalysisRequest):
    """Process restaurant analysis job using GPT-5"""
    try:
        # Update job status
        jobs[job_id]["status"] = "running"
        jobs[job_id]["message"] = "Analyzing restaurant with GPT-5..."
        
        logger.info(f"Starting GPT-5 analysis for job {job_id}: {request.restaurant_name}")
        
        # Call GPT-5 for real analysis
        analysis_result = await analyze_restaurant_with_gpt5(
            request.restaurant_name, 
            request.address,
            request.phone
        )
        
        # Complete job
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = analysis_result
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["message"] = "GPT-5 analysis completed successfully"
        
        logger.info(f"Job {job_id} completed successfully - GPT-5 tokens: {analysis_result.get('tokens_used', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"GPT-5 analysis failed: {str(e)}"

@app.get("/health")
async def health_check():
    """Health check endpoint for AWS App Runner"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/analyze", response_model=AnalysisResponse)
async def create_analysis_job(request: AnalysisRequest):
    """Create a new restaurant analysis job"""
    job_id = f"job_{int(datetime.now().timestamp())}_{hash(request.restaurant_name) % 10000}"
    
    # Create job record
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "message": "Analysis job created and queued",
        "created_at": datetime.now().isoformat(),
        "request": request.dict(),
        "result": None,
        "completed_at": None
    }
    
    # Start processing in background
    asyncio.create_task(process_analysis_job(job_id, request))
    
    return AnalysisResponse(
        job_id=job_id,
        status="queued",
        message="Analysis job created successfully"
    )

@app.get("/api/job/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status and results"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return JobStatus(**job)

# Initialize DynamoDB
try:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    restaurants_table = dynamodb.Table('restaurants')
    logger.info("Connected to DynamoDB restaurants table")
except Exception as e:
    logger.error(f"Failed to connect to DynamoDB: {e}")
    restaurants_table = None

@app.get("/api/restaurants/search")
async def search_restaurants(query: str = "", limit: int = 20):
    """Search restaurants from DynamoDB"""
    
    if not restaurants_table:
        # Fallback data if DynamoDB not available
        fallback_restaurants = [
            {
                "id": "1",
                "name": "DUKES RESTAURANT",
                "address": "1216 PROSPECT ST",
                "city": "LA JOLLA",
                "state": "CA",
                "zip": "92037",
                "phone": "858-454-5888",
                "business_type": "Restaurant Food Facility"
            }
        ]
        return {"restaurants": fallback_restaurants}
    
    try:
        if query:
            # For case-insensitive search, scan all and filter in Python
            # (For large datasets, consider using DynamoDB Global Secondary Indexes)
            query_lower = query.lower()
            response = restaurants_table.scan(
                FilterExpression=Attr('active').eq(True)
            )
            
            # Filter results case-insensitively in Python
            all_restaurants = response.get('Items', [])
            filtered_restaurants = [
                r for r in all_restaurants
                if (query_lower in r.get('name', '').lower() or 
                    query_lower in r.get('address', '').lower() or
                    query_lower in r.get('city', '').lower())
            ]
            
            # Apply limit
            restaurants = filtered_restaurants[:limit]
        else:
            # Get all active restaurants
            response = restaurants_table.scan(
                FilterExpression=Attr('active').eq(True),
                Limit=limit
            )
            restaurants = response.get('Items', [])
        
        # Convert Decimal to float for JSON serialization
        def convert_decimals(obj):
            if hasattr(obj, 'to_eng_string'):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(v) for v in obj]
            return obj
        
        restaurants = convert_decimals(restaurants)
        return {"restaurants": restaurants}
        
    except Exception as e:
        logger.error(f"Error searching restaurants: {e}")
        return {"restaurants": [], "error": str(e)}

@app.get("/api/jobs")
async def list_jobs():
    """List all jobs for debugging"""
    return {"jobs": list(jobs.keys()), "total": len(jobs)}

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "GPT-5 Happy Hour Orchestrator",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/api/analyze",
            "/api/job/{job_id}",
            "/api/restaurants/search"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
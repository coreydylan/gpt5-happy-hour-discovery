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

# Mock data for testing - replace with real GPT-5 analysis
def generate_mock_analysis(restaurant_name: str, address: str) -> Dict[str, Any]:
    """Generate mock analysis data for testing"""
    return {
        "restaurant_name": restaurant_name,
        "address": address,
        "analysis": {
            "happy_hour_confirmed": True,
            "happy_hour_times": "Monday-Friday 3:00 PM - 6:00 PM",
            "happy_hour_deals": [
                "$5 draft beers",
                "$8 wine selections", 
                "$12 appetizer specials"
            ],
            "confidence_score": 0.85,
            "verification_method": "website_analysis",
            "last_updated": datetime.now().isoformat(),
            "sources": [
                "restaurant_website",
                "google_business_listing"
            ]
        },
        "contact_verification": {
            "phone_verified": True,
            "website_active": True,
            "social_media_active": True
        }
    }

async def process_analysis_job(job_id: str, request: AnalysisRequest):
    """Process restaurant analysis job"""
    try:
        # Update job status
        jobs[job_id]["status"] = "running"
        jobs[job_id]["message"] = "Analyzing restaurant data..."
        
        # Simulate processing time
        await asyncio.sleep(5)
        
        # Generate analysis (replace with real GPT-5 processing)
        analysis_result = generate_mock_analysis(
            request.restaurant_name, 
            request.address
        )
        
        # Complete job
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = analysis_result
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["message"] = "Analysis completed successfully"
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Analysis failed: {str(e)}"

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

@app.get("/api/restaurants/search")
async def search_restaurants(query: str = "", limit: int = 20):
    """Search La Jolla restaurants"""
    # La Jolla restaurant database
    restaurants_db = [
        {
            "id": "1",
            "name": "DUKES RESTAURANT",
            "address": "1216 PROSPECT ST, LA JOLLA, CA 92037",
            "phone": "858-454-5888",
            "business_type": "Restaurant Food Facility",
            "city": "LA JOLLA"
        },
        {
            "id": "2", 
            "name": "BARBARELLA RESTAURANT",
            "address": "2171 AVENIDA DE LA PLAYA, LA JOLLA, CA 92037",
            "phone": "858-242-2589",
            "business_type": "Restaurant Food Facility",
            "city": "LA JOLLA"
        },
        {
            "id": "3",
            "name": "EDDIE VS #8511", 
            "address": "1270 PROSPECT ST, LA JOLLA, CA 92037",
            "phone": "858-459-5500",
            "business_type": "Restaurant Food Facility",
            "city": "LA JOLLA"
        },
        {
            "id": "4",
            "name": "THE PRADO RESTAURANT",
            "address": "1549 EL PRADO, LA JOLLA, CA 92037", 
            "phone": "858-454-1549",
            "business_type": "Restaurant Food Facility",
            "city": "LA JOLLA"
        },
        {
            "id": "5",
            "name": "GEORGE'S AT THE COVE",
            "address": "1250 PROSPECT ST, LA JOLLA, CA 92037", 
            "phone": "858-454-4244",
            "business_type": "Restaurant Food Facility",
            "city": "LA JOLLA"
        },
        {
            "id": "6",
            "name": "THE MARINE ROOM",
            "address": "2000 SPINDRIFT DR, LA JOLLA, CA 92037", 
            "phone": "858-459-7222",
            "business_type": "Restaurant Food Facility",
            "city": "LA JOLLA"
        },
        {
            "id": "7",
            "name": "HERRINGBONE LA JOLLA",
            "address": "7837 HERSCHEL AVE, LA JOLLA, CA 92037", 
            "phone": "858-459-0221",
            "business_type": "Restaurant Food Facility",
            "city": "LA JOLLA"
        },
        {
            "id": "8",
            "name": "PUESTO LA JOLLA",
            "address": "1026 WALL ST, LA JOLLA, CA 92037", 
            "phone": "858-454-1026",
            "business_type": "Restaurant Food Facility",
            "city": "LA JOLLA"
        }
    ]
    
    # Filter restaurants based on query
    if query:
        filtered_restaurants = [
            r for r in restaurants_db 
            if query.lower() in r["name"].lower() or query.lower() in r["address"].lower()
        ]
    else:
        filtered_restaurants = restaurants_db
    
    # Apply limit
    limited_restaurants = filtered_restaurants[:limit]
    
    return {"restaurants": limited_restaurants}

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
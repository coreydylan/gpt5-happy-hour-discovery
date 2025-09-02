"""
Vercel API Handler for GPT-5 Happy Hour Discovery System
Deployed version of the orchestrator service
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Happy Hour Discovery API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

class RestaurantLookupRequest(BaseModel):
    """Request to analyze a restaurant"""
    name: str = Field(..., description="Restaurant name")
    address: Optional[str] = Field(None, description="Restaurant address")
    phone: Optional[str] = Field(None, description="Restaurant phone")
    website: Optional[str] = Field(None, description="Restaurant website")
    priority: int = Field(5, description="Priority: 1 (highest) to 10 (lowest)")

class AnalysisResponse(BaseModel):
    """Response from analysis request"""
    job_id: str
    venue_id: str
    status: str
    message: str
    estimated_time_seconds: int = 45

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Happy Hour Discovery API",
        "version": "1.0.0",
        "gpt_version": "GPT-5 Exclusive"
    }

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_restaurant(request: RestaurantLookupRequest):
    """Analyze a restaurant for happy hour information"""
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    try:
        # Get or create venue
        venue_result = supabase.table('venues').select('id').eq('name', request.name).execute()
        
        if venue_result.data and len(venue_result.data) > 0:
            venue_id = venue_result.data[0]['id']
        else:
            # Parse address for city and state
            city = None
            state = None
            if request.address:
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
                'phone_e164': request.phone,
                'website': request.website,
                'created_at': datetime.utcnow().isoformat()
            }
            
            supabase.table('venues').insert(venue_data).execute()
            venue_id = venue_data['id']
        
        # Create analysis job
        job_id = str(uuid.uuid4())
        job_data = {
            'id': job_id,
            'venue_id': venue_id,
            'status': 'queued',
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
        
        supabase.table('analysis_jobs').insert(job_data).execute()
        
        # Note: In production, this would trigger Lambda functions or background workers
        # For now, we're just creating the job record
        
        return AnalysisResponse(
            job_id=job_id,
            venue_id=venue_id,
            status="queued",
            message="Analysis job created. Agents will process shortly.",
            estimated_time_seconds=45
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating analysis job: {str(e)}")

@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of an analysis job"""
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    try:
        result = supabase.table('analysis_jobs').select('*').eq('id', job_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = result.data[0]
        
        # Get happy hour data if job is completed
        happy_hour_data = None
        if job['status'] == 'completed' and job['venue_id']:
            hh_result = supabase.table('happy_hour_records').select('*').eq('venue_id', job['venue_id']).execute()
            if hh_result.data and len(hh_result.data) > 0:
                happy_hour_data = hh_result.data[0]
        
        return {
            'job_id': job['id'],
            'status': job['status'],
            'venue_id': job['venue_id'],
            'started_at': job['started_at'],
            'completed_at': job.get('completed_at'),
            'confidence_score': job.get('final_confidence'),
            'happy_hour_data': happy_hour_data,
            'error_message': job.get('error_message')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job status: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    try:
        # Get total venues
        venues_result = supabase.table('venues').select('id', count='exact').execute()
        total_venues = venues_result.count if venues_result else 0
        
        # Get total jobs
        jobs_result = supabase.table('analysis_jobs').select('id', count='exact').execute()
        total_jobs = jobs_result.count if jobs_result else 0
        
        # Get jobs by status
        queued_result = supabase.table('analysis_jobs').select('id', count='exact').eq('status', 'queued').execute()
        completed_result = supabase.table('analysis_jobs').select('id', count='exact').eq('status', 'completed').execute()
        
        return {
            'total_venues': total_venues,
            'total_jobs': total_jobs,
            'queued_jobs': queued_result.count if queued_result else 0,
            'completed_jobs': completed_result.count if completed_result else 0,
            'system_status': 'operational'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

# Handler for Vercel
handler = app
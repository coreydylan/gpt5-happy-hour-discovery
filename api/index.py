#!/usr/bin/env python3
"""
Vercel-optimized FastAPI Backend for GPT-5 Happy Hour Discovery
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our GPT-5 system
try:
    from proper_gpt5_system import ProperGPT5System
except ImportError:
    # Fallback import for Vercel
    import importlib.util
    spec = importlib.util.spec_from_file_location("proper_gpt5_system", "../proper_gpt5_system.py")
    proper_gpt5_system = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(proper_gpt5_system)
    ProperGPT5System = proper_gpt5_system.ProperGPT5System

app = FastAPI(title="GPT-5 Happy Hour Discovery API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Vercel deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global system instance
gpt5_system = None

# Pydantic models
class RestaurantSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class HappyHourRequest(BaseModel):
    restaurant_name: str
    address: str
    phone: Optional[str] = None
    business_type: Optional[str] = "Restaurant"

# Global restaurants data
restaurants_df = None

async def initialize():
    """Initialize the system and load data"""
    global gpt5_system, restaurants_df
    
    if gpt5_system is None:
        gpt5_system = ProperGPT5System()
    
    if restaurants_df is None:
        try:
            # Try to load CSV from parent directory
            csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "food_permits_restaurants.csv")
            restaurants_df = pd.read_csv(csv_path)
            print(f"✅ Loaded {len(restaurants_df)} restaurants from CSV")
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            # Create empty dataframe as fallback
            restaurants_df = pd.DataFrame()

@app.on_event("startup")
async def startup_event():
    await initialize()

@app.get("/")
async def root():
    return {
        "message": "GPT-5 Happy Hour Discovery API", 
        "status": "running",
        "deployed_on": "Vercel",
        "model": "gpt-5-2025-08-07"
    }

@app.get("/health")
async def health_check():
    await initialize()
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "restaurants_loaded": len(restaurants_df) if restaurants_df is not None else 0,
        "gpt5_system": "initialized" if gpt5_system else "not initialized"
    }

@app.get("/api/restaurants/search")
async def search_restaurants(query: str = "", limit: int = 20):
    """Search for restaurants by name"""
    try:
        await initialize()
        
        if restaurants_df is None or restaurants_df.empty:
            # Return sample data if CSV not available
            sample_restaurants = [
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
                }
            ]
            
            if query:
                filtered_restaurants = [r for r in sample_restaurants if query.lower() in r['name'].lower()]
            else:
                filtered_restaurants = sample_restaurants
                
            return {
                "restaurants": filtered_restaurants[:limit],
                "total": len(filtered_restaurants),
                "query": query,
                "data_source": "sample_data"
            }
        
        if query:
            filtered = restaurants_df[
                restaurants_df['Record Name'].str.contains(query, case=False, na=False)
            ]
        else:
            filtered = restaurants_df
        
        results = filtered.head(limit)
        
        restaurants = []
        for _, row in results.iterrows():
            restaurants.append({
                "id": str(row.get('id', '')),
                "name": row['Record Name'],
                "address": f"{row['Address']}, {row['City']}, {row['State']} {row['Zip']}",
                "phone": row.get('Permit Owner Business Phone', ''),
                "business_type": row.get('Business Type', 'Restaurant'),
                "city": row['City']
            })
        
        return {
            "restaurants": restaurants,
            "total": len(restaurants),
            "query": query,
            "data_source": "csv_file"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.post("/api/analyze")
async def analyze_happy_hour(request: HappyHourRequest):
    """Analyze a restaurant for happy hour using GPT-5"""
    try:
        await initialize()
        
        if not gpt5_system:
            raise HTTPException(status_code=500, detail="GPT-5 system not initialized")
        
        # Create restaurant dict for our system
        restaurant_data = {
            'Record Name': request.restaurant_name,
            'Address': request.address.split(',')[0] if ',' in request.address else request.address,
            'City': 'La Jolla',
            'State': 'CA',
            'Zip': '92037',
            'Permit Owner Business Phone': request.phone,
            'Business Type': request.business_type
        }
        
        print(f"🔍 Analyzing {request.restaurant_name} with GPT-5...")
        
        # Use our GPT-5 system
        result = await gpt5_system.discover_happy_hour_responses_api(restaurant_data)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
    
    except Exception as e:
        print(f"❌ Error in analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    try:
        await initialize()
        
        total_restaurants = len(restaurants_df) if restaurants_df is not None else 0
        
        return {
            "total_restaurants": total_restaurants,
            "analyzed_restaurants": 0,  # Would track this with a database
            "gpt5_model": "gpt-5-2025-08-07",
            "api_type": "responses_api",
            "deployment": "vercel"
        }
    
    except Exception as e:
        return {"error": str(e)}

# Handle all routes for Vercel
@app.get("/api/{path:path}")
async def catch_all_get(path: str):
    return {"message": f"GET endpoint /{path} not found", "available_endpoints": ["/", "/health", "/api/restaurants/search", "/api/stats"]}

@app.post("/api/{path:path}")
async def catch_all_post(path: str):
    return {"message": f"POST endpoint /{path} not found", "available_endpoints": ["/api/analyze"]}

# For Vercel serverless function
def handler(request):
    return app(request)

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
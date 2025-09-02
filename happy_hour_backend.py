#!/usr/bin/env python3
"""
FastAPI Backend for GPT-5 Happy Hour Discovery
Provides REST API for React frontend
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
import uvicorn

# Import our GPT-5 system
from proper_gpt5_system import ProperGPT5System

app = FastAPI(title="GPT-5 Happy Hour Discovery API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global system instance
gpt5_system = ProperGPT5System()

# Pydantic models
class RestaurantSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class HappyHourRequest(BaseModel):
    restaurant_name: str
    address: str
    phone: Optional[str] = None
    business_type: Optional[str] = "Restaurant"

class HappyHourResponse(BaseModel):
    restaurant_name: str
    gpt5_analysis: str
    model_used: str
    api_type: str
    tokens_used: Optional[int]
    reasoning_tokens: Optional[int]
    reasoning_effort: Optional[str]
    timestamp: str

# Load restaurant data once at startup
try:
    restaurants_df = pd.read_csv("food_permits_restaurants.csv")
    print(f"✅ Loaded {len(restaurants_df)} restaurants from CSV")
except Exception as e:
    print(f"❌ Error loading CSV: {e}")
    restaurants_df = pd.DataFrame()

@app.get("/")
async def root():
    return {"message": "GPT-5 Happy Hour Discovery API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/restaurants/search")
async def search_restaurants(query: str = "", limit: int = 20):
    """Search for restaurants by name"""
    try:
        if restaurants_df.empty:
            raise HTTPException(status_code=500, detail="Restaurant data not loaded")
        
        if query:
            # Search by name (case insensitive)
            filtered = restaurants_df[
                restaurants_df['Record Name'].str.contains(query, case=False, na=False)
            ]
        else:
            filtered = restaurants_df
        
        # Limit results
        results = filtered.head(limit)
        
        # Convert to list of dicts
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
            "query": query
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_happy_hour(request: HappyHourRequest):
    """Analyze a restaurant for happy hour using GPT-5"""
    try:
        # Create restaurant dict for our system
        restaurant_data = {
            'Record Name': request.restaurant_name,
            'Address': request.address.split(',')[0] if ',' in request.address else request.address,
            'City': 'La Jolla',  # Default for our dataset
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/batch")
async def analyze_batch(restaurant_names: List[str]):
    """Analyze multiple restaurants in batch"""
    try:
        if len(restaurant_names) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 restaurants per batch")
        
        results = []
        for name in restaurant_names:
            # Find restaurant in CSV
            matches = restaurants_df[
                restaurants_df['Record Name'].str.contains(name, case=False, na=False)
            ]
            
            if not matches.empty:
                restaurant = matches.iloc[0].to_dict()
                result = await gpt5_system.discover_happy_hour_responses_api(restaurant)
                results.append(result)
                
                # Brief pause between requests
                await asyncio.sleep(0.5)
        
        return {"results": results, "total": len(results)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        total_restaurants = len(restaurants_df) if not restaurants_df.empty else 0
        
        # Check for existing results
        result_files = ["proper_gpt5_results.json", "working_happy_hour_results.json"]
        analyzed_count = 0
        
        for file in result_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    analyzed_count += len(data)
            except:
                continue
        
        return {
            "total_restaurants": total_restaurants,
            "analyzed_restaurants": analyzed_count,
            "gpt5_model": "gpt-5-2025-08-07",
            "api_type": "responses_api"
        }
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting GPT-5 Happy Hour Discovery API")
    print("🌐 API will be available at: http://localhost:8000")
    print("📚 API docs at: http://localhost:8000/docs")
    
    uvicorn.run(
        "happy_hour_backend:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
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
import openai

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Inline GPT-5 system to avoid import issues

class SimpleGPT5System:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def discover_happy_hour_responses_api(self, restaurant_data):
        """Analyze restaurant for happy hour using GPT-5 Responses API"""
        try:
            prompt = f"""
            Analyze this La Jolla restaurant for happy hour information:
            
            Name: {restaurant_data.get('Record Name', 'Unknown')}
            Address: {restaurant_data.get('Address', '')}, {restaurant_data.get('City', '')}, {restaurant_data.get('State', '')}
            Business Type: {restaurant_data.get('Business Type', 'Restaurant')}
            Phone: {restaurant_data.get('Permit Owner Business Phone', '')}
            
            Based on your knowledge, provide a comprehensive analysis of this restaurant's likely happy hour offerings.
            Consider the location (La Jolla is upscale), business type, and typical industry practices.
            
            Return your analysis in this exact JSON format:
            {{
                "restaurant_name": "{restaurant_data.get('Record Name', 'Unknown')}",
                "gpt5_analysis": "Detailed analysis of happy hour likelihood, typical schedule, and expected offerings based on restaurant type and location",
                "model_used": "gpt-5",
                "api_type": "responses_api", 
                "tokens_used": 0,
                "reasoning_tokens": 0,
                "reasoning_effort": "medium",
                "timestamp": "{datetime.now().isoformat()}"
            }}
            """
            
            # Use GPT-5 Responses API
            response = await self.client.responses.create(
                model="gpt-5",
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                modalities=["text"],
                max_completion_tokens=1500
            )
            
            # Extract the analysis
            analysis_text = response.choices[0].message.content
            
            return {
                "restaurant_name": restaurant_data.get('Record Name', 'Unknown'),
                "gpt5_analysis": analysis_text,
                "model_used": "gpt-5", 
                "api_type": "responses_api",
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                "reasoning_tokens": response.usage.reasoning_tokens if hasattr(response, 'usage') and hasattr(response.usage, 'reasoning_tokens') else 0,
                "reasoning_effort": "medium",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "restaurant_name": restaurant_data.get('Record Name', 'Unknown'),
                "error": f"GPT-5 analysis failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

ProperGPT5System = SimpleGPT5System

app = FastAPI(title="GPT-5 Happy Hour Discovery API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost:3000", 
        "https://happy-hour-frontend-3zc7123lu-experial.vercel.app",
        "https://happy-hour-frontend-5o4byosgn-experial.vercel.app",
        "https://happy-hour-frontend-dp30ckd8d-experial.vercel.app",
        "https://happy-hour-frontend.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
    
    # Always use sample data for Vercel deployment to avoid file path issues
    restaurants_df = pd.DataFrame()
    print("✅ Using sample restaurant data for Vercel deployment")

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
        print(f"🔍 Search request: query='{query}', limit={limit}")
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
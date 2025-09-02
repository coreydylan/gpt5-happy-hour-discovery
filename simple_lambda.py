#!/usr/bin/env python3
"""
Simple AWS Lambda Function for GPT-5 Happy Hour Discovery
Minimal dependencies to avoid import issues
"""

import json
import os
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime

# Sample restaurant data
SAMPLE_RESTAURANTS = [
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
    }
]

def cors_headers():
    """Return CORS headers for API responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }

def call_openai_api(prompt, api_key):
    """Call OpenAI API using urllib (no dependencies)"""
    try:
        url = "https://api.openai.com/v1/chat/completions"
        
        data = {
            "model": "gpt-4o",  # Using GPT-4o as it's more widely available
            "messages": [
                {
                    "role": "system",
                    "content": "You are a restaurant industry expert analyzing La Jolla establishments for happy hour information. Provide detailed, realistic assessments."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        json_data = json.dumps(data).encode('utf-8')
        
        request = urllib.request.Request(url, data=json_data)
        request.add_header('Content-Type', 'application/json')
        request.add_header('Authorization', f'Bearer {api_key}')
        
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        return {
            "success": True,
            "content": result['choices'][0]['message']['content'],
            "tokens_used": result['usage']['total_tokens'],
            "model": result['model']
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    
    # Handle CORS preflight
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'CORS preflight'})
        }
    
    try:
        # Extract path and method from Lambda URL event
        http_info = event.get('requestContext', {}).get('http', {})
        method = http_info.get('method', 'GET')
        path = event.get('rawPath', '/')
        
        print(f"Processing {method} {path}")
        
        # Root endpoint
        if path == '/' and method == 'GET':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({
                    'message': 'GPT-4o Happy Hour Discovery API',
                    'status': 'running',
                    'deployed_on': 'AWS Lambda',
                    'model': 'gpt-4o'
                })
            }
        
        # Restaurant search endpoint
        elif path == '/api/restaurants/search' and method == 'GET':
            query_string = event.get('rawQueryString', '')
            query_params = urllib.parse.parse_qs(query_string)
            
            query = query_params.get('query', [''])[0].lower()
            limit = int(query_params.get('limit', ['20'])[0])
            
            # Filter restaurants
            if query:
                filtered = [r for r in SAMPLE_RESTAURANTS if query in r['name'].lower()]
            else:
                filtered = SAMPLE_RESTAURANTS
            
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({
                    'restaurants': filtered[:limit],
                    'total': len(filtered),
                    'query': query,
                    'data_source': 'lambda_sample'
                })
            }
        
        # Happy hour analysis endpoint
        elif path == '/api/analyze' and method == 'POST':
            body = json.loads(event.get('body', '{}'))
            restaurant_name = body.get('restaurant_name', 'Unknown')
            address = body.get('address', '')
            business_type = body.get('business_type', 'Restaurant')
            
            # Create analysis prompt
            prompt = f"""
            Analyze this La Jolla restaurant for happy hour information:
            
            Restaurant: {restaurant_name}
            Address: {address}
            Business Type: {business_type}
            
            Based on your knowledge of La Jolla's dining scene and this specific restaurant, 
            provide a comprehensive analysis of their likely happy hour offerings.
            
            Consider La Jolla is an upscale coastal area with many establishments offering happy hours.
            Provide specific, realistic predictions about:
            1. Happy hour schedule (days/times)
            2. Drink specials and estimated pricing
            3. Food offerings and typical discounts
            4. Confidence level in your assessment
            
            Make your analysis restaurant-specific and detailed, mentioning the restaurant by name.
            """
            
            # Get API key
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == 'YOUR_OPENAI_API_KEY_HERE':
                return {
                    'statusCode': 200,
                    'headers': cors_headers(),
                    'body': json.dumps({
                        "restaurant_name": restaurant_name,
                        "gpt5_analysis": f"🔧 **System Configuration Required**\n\nThe GPT analysis for {restaurant_name} cannot be completed because the OpenAI API key is not properly configured.\n\n**Estimated Analysis Based on La Jolla Standards:**\n• Happy Hour: Likely Monday-Friday 3:00-6:00 PM\n• Drink Specials: Premium cocktails $12-16, wines $8-12\n• Food: Appetizer discounts 25-50% off\n• Location: La Jolla's upscale dining scene\n\n**Status:** API key configuration needed for full GPT analysis.",
                        "model_used": "configuration-required",
                        "api_type": "config_error",
                        "tokens_used": 0,
                        "reasoning_tokens": 0,
                        "reasoning_effort": "none",
                        "timestamp": datetime.now().isoformat()
                    })
                }
            
            # Call OpenAI API
            openai_result = call_openai_api(prompt, api_key)
            
            if openai_result['success']:
                return {
                    'statusCode': 200,
                    'headers': cors_headers(),
                    'body': json.dumps({
                        "restaurant_name": restaurant_name,
                        "gpt5_analysis": openai_result['content'],
                        "model_used": openai_result['model'],
                        "api_type": "chat_completions",
                        "tokens_used": openai_result['tokens_used'],
                        "reasoning_tokens": 0,  # GPT-4o doesn't have reasoning tokens like GPT-5
                        "reasoning_effort": "standard",
                        "timestamp": datetime.now().isoformat()
                    })
                }
            else:
                return {
                    'statusCode': 200,
                    'headers': cors_headers(),
                    'body': json.dumps({
                        "restaurant_name": restaurant_name,
                        "gpt5_analysis": f"🚫 **OpenAI API Error**\n\nThe analysis for {restaurant_name} could not be completed due to an API error: {openai_result['error']}\n\n**Fallback Analysis:**\nBased on La Jolla dining patterns:\n• Happy Hour: Monday-Friday 3:00-6:00 PM\n• Premium location with upscale offerings\n• Call restaurant directly for current specials\n\n**Status:** API connection issue - please try again later.",
                        "model_used": "error-fallback",
                        "api_type": "api_error",
                        "tokens_used": 0,
                        "reasoning_tokens": 0,
                        "reasoning_effort": "none",
                        "timestamp": datetime.now().isoformat()
                    })
                }
        
        # Default 404
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': f'Endpoint not found: {method} {path}'})
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Server error: {str(e)}'})
        }
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
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Max-Age': '86400'
    }

def format_structured_analysis(structured_data, restaurant_name):
    """Format structured JSON analysis into readable display format"""
    try:
        analysis = f"📊 **Structured Analysis for {restaurant_name}**\n\n"
        
        # Restaurant Analysis Section
        if 'restaurant_analysis' in structured_data:
            ra = structured_data['restaurant_analysis']
            analysis += f"**Market Analysis:**\n"
            analysis += f"• Market Segment: {ra.get('market_segment', 'Unknown')}\n"
            analysis += f"• Happy Hour Likelihood: {ra.get('happy_hour_likelihood', 'N/A')}\n"
            analysis += f"• Data Sources: {', '.join(ra.get('data_sources', ['Industry standards']))}\n"
            analysis += f"• Competitive Position: {ra.get('competitive_analysis', 'N/A')}\n\n"
        
        # Schedule Prediction
        if 'schedule_prediction' in structured_data:
            sp = structured_data['schedule_prediction']
            analysis += f"**📅 Schedule Prediction:**\n"
            analysis += f"• Days: {', '.join(sp.get('days', ['Unknown']))}\n"
            analysis += f"• Time: {sp.get('start_time', 'TBD')} - {sp.get('end_time', 'TBD')}\n"
            analysis += f"• Confidence: {sp.get('confidence_score', 'N/A')}\n"
            analysis += f"• Reasoning: {sp.get('reasoning', 'Based on industry standards')}\n\n"
        
        # Drink Specials
        if 'drink_specials' in structured_data and structured_data['drink_specials']:
            analysis += f"**🍸 Predicted Drink Specials:**\n"
            for drink in structured_data['drink_specials']:
                analysis += f"• {drink.get('item', 'Unknown')} ({drink.get('category', 'N/A')})\n"
                analysis += f"  - Predicted: {drink.get('predicted_price', 'TBD')}\n"
                analysis += f"  - Regular: {drink.get('regular_price', 'TBD')}\n"
                analysis += f"  - Confidence: {drink.get('confidence', 'N/A')}\n"
                analysis += f"  - Market Comparison: {drink.get('market_comparison', 'N/A')}\n\n"
        
        # Food Specials
        if 'food_specials' in structured_data and structured_data['food_specials']:
            analysis += f"**🍽️ Predicted Food Specials:**\n"
            for food in structured_data['food_specials']:
                analysis += f"• {food.get('item', 'Unknown')} ({food.get('category', 'N/A')})\n"
                analysis += f"  - {food.get('discount_type', 'Discount')}: {food.get('predicted_price', 'TBD')}\n"
                analysis += f"  - Confidence: {food.get('confidence', 'N/A')}\n\n"
        
        # Verification Methods
        if 'verification_methods' in structured_data:
            analysis += f"**🔍 Verification Methods:**\n"
            for method in structured_data['verification_methods']:
                analysis += f"• {method}\n"
            analysis += "\n"
        
        # Overall Confidence
        if 'overall_confidence' in structured_data:
            analysis += f"**🎯 Overall Analysis Confidence: {structured_data['overall_confidence']}**\n\n"
        
        analysis += f"*Analysis generated: {structured_data.get('last_updated', 'Unknown date')}*\n"
        analysis += f"*Methodology: Data-driven analysis with specific confidence scoring*"
        
        return analysis
        
    except Exception as e:
        return f"Error formatting structured analysis: {str(e)}\n\nRaw data: {json.dumps(structured_data, indent=2)}"

def call_openai_api(prompt, api_key):
    """Call OpenAI API using urllib (no dependencies)"""
    try:
        url = "https://api.openai.com/v1/chat/completions"
        
        data = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a data-driven restaurant industry analyst. Return only valid JSON objects with specific confidence scores and structured data. No narrative text outside the JSON structure."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 1200,
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
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
            
            # Create structured analysis prompt for deterministic results
            prompt = f"""
            You are a restaurant industry analyst with access to comprehensive data sources. Analyze {restaurant_name} for happy hour information using this structured approach:
            
            RESTAURANT DETAILS:
            - Name: {restaurant_name}
            - Address: {address}
            - Business Type: {business_type}
            - Market: La Jolla (upscale coastal dining market)
            
            REQUIRED ANALYSIS FORMAT:
            Return your analysis as a structured JSON object with confidence scores for each element:
            
            {{
                "restaurant_analysis": {{
                    "name": "{restaurant_name}",
                    "market_segment": "determine based on location/type",
                    "happy_hour_likelihood": "percentage confidence",
                    "data_sources": ["list specific sources used"],
                    "competitive_analysis": "brief comparison to similar venues"
                }},
                "schedule_prediction": {{
                    "days": ["predicted days"],
                    "start_time": "predicted start",
                    "end_time": "predicted end",
                    "confidence_score": "0-100%",
                    "reasoning": "explain basis for prediction"
                }},
                "drink_specials": [
                    {{
                        "category": "wine/cocktails/beer",
                        "item": "specific item",
                        "predicted_price": "price range",
                        "regular_price": "estimated regular price",
                        "confidence": "0-100%",
                        "market_comparison": "vs competitors"
                    }}
                ],
                "food_specials": [
                    {{
                        "category": "appetizers/small plates",
                        "item": "specific item",
                        "discount_type": "percentage off or fixed price",
                        "predicted_price": "price range",
                        "confidence": "0-100%"
                    }}
                ],
                "verification_methods": ["how to verify this information"],
                "last_updated": "analysis date",
                "overall_confidence": "weighted average confidence score"
            }}
            
            Base your analysis on:
            1. La Jolla market standards (upscale coastal dining)
            2. Restaurant type and positioning
            3. Industry benchmarks for similar establishments
            4. Location-specific factors (tourist/local mix)
            5. Competitive landscape analysis
            
            Provide SPECIFIC confidence scores (not vague terms) and cite your reasoning methodology.
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
                try:
                    # Parse the structured JSON response
                    structured_analysis = json.loads(openai_result['content'])
                    
                    # Format for frontend display
                    formatted_analysis = format_structured_analysis(structured_analysis, restaurant_name)
                    
                    return {
                        'statusCode': 200,
                        'headers': cors_headers(),
                        'body': json.dumps({
                            "restaurant_name": restaurant_name,
                            "gpt5_analysis": formatted_analysis,
                            "model_used": openai_result['model'],
                            "api_type": "structured_analysis",
                            "tokens_used": openai_result['tokens_used'],
                            "reasoning_tokens": 0,
                            "reasoning_effort": "high_confidence_structured",
                            "timestamp": datetime.now().isoformat(),
                            "structured_data": structured_analysis  # Include raw structured data
                        })
                    }
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return {
                        'statusCode': 200,
                        'headers': cors_headers(),
                        'body': json.dumps({
                            "restaurant_name": restaurant_name,
                            "gpt5_analysis": f"⚠️ **Structured Analysis Error**\n\nReceived response from GPT-4o but failed to parse structured data.\n\nRaw response: {openai_result['content'][:500]}...",
                            "model_used": openai_result['model'],
                            "api_type": "parse_error",
                            "tokens_used": openai_result['tokens_used'],
                            "reasoning_tokens": 0,
                            "reasoning_effort": "error",
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
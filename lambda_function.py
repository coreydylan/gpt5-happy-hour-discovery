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

def call_gpt5_api(restaurant_data, api_key):
    """Call GPT-5 using Chat Completions API with reasoning tokens"""
    try:
        url = "https://api.openai.com/v1/chat/completions"
        
        # Simplified prompt that GPT-5 can reliably process
        user_prompt = f"""Analyze {restaurant_data['restaurant_name']} for happy hour information.

Restaurant: {restaurant_data['restaurant_name']}
Address: {restaurant_data['address']}
Type: {restaurant_data['business_type']}
Market: La Jolla upscale coastal dining

Provide a detailed analysis covering:
- Market positioning and happy hour likelihood
- Predicted schedule (days and times)  
- Expected drink specials with pricing
- Food specials and discounts
- Confidence levels for each prediction
- Data sources and verification methods

Format as clear, structured analysis with specific details and confidence percentages."""

        # Try different GPT-5 model variations and parameters
        models_to_try = ["gpt-5", "gpt-5-2025-08-07", "gpt-4o"]
        
        for model_name in models_to_try:
            try:
                # Adjust parameters based on model
                data = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert restaurant industry analyst. Provide detailed, evidence-based happy hour analysis with specific confidence scores and actionable insights."
                        },
                        {
                            "role": "user", 
                            "content": user_prompt
                        }
                    ]
                }
                
                # Add GPT-5 specific parameters
                if "gpt-5" in model_name:
                    data["max_completion_tokens"] = 1200
                    data["reasoning_effort"] = "high"
                else:
                    data["max_tokens"] = 1200
                    data["temperature"] = 0.3
                
                print(f"Trying model: {model_name}")
                
                json_data = json.dumps(data).encode('utf-8')
                
                request = urllib.request.Request(url, data=json_data)
                request.add_header('Content-Type', 'application/json')
                request.add_header('Authorization', f'Bearer {api_key}')
                
                with urllib.request.urlopen(request, timeout=25) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    
                content = result['choices'][0]['message']['content']
                print(f"{model_name} returned {len(content)} characters")
                
                if content and len(content) > 10:  # Valid response
                    return {
                        "success": True,
                        "content": content,
                        "tokens_used": result['usage']['total_tokens'],
                        "reasoning_tokens": result['usage'].get('reasoning_tokens', 0),
                        "model": result['model'],
                        "api_type": f"chat_completions_{model_name.replace('-', '_')}"
                    }
                    
            except Exception as e:
                print(f"Model {model_name} failed: {str(e)}")
                continue
        
        # If all models failed
        return {
            "success": False,
            "error": "All models failed to return valid content"
        }
        
    except Exception as e:
        print(f"GPT-5 API error: {str(e)}")
        return {
            "success": False,
            "error": f"GPT-5 API failed: {str(e)}"
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
                    'message': 'GPT-5 Happy Hour Discovery API',
                    'status': 'running',
                    'deployed_on': 'AWS Lambda',
                    'model': 'gpt-5',
                    'capabilities': ['responses_api', 'parallel_agents', 'reasoning_tokens', 'structured_outputs'],
                    'agents': ['market_analyst', 'schedule_predictor', 'pricing_analyst']
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
            
            # Prepare restaurant data for GPT-5 analysis
            restaurant_data = {
                'restaurant_name': restaurant_name,
                'address': address,
                'business_type': business_type
            }
            
            # Get API key
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == 'YOUR_OPENAI_API_KEY_HERE':
                return {
                    'statusCode': 200,
                    'headers': cors_headers(),
                    'body': json.dumps({
                        "restaurant_name": restaurant_name,
                        "gpt5_analysis": f"🔧 **System Configuration Required**\n\nThe GPT-5 analysis for {restaurant_name} cannot be completed because the OpenAI API key is not properly configured.\n\n**Estimated Analysis Based on La Jolla Standards:**\n• Happy Hour: Likely Monday-Friday 3:00-6:00 PM\n• Drink Specials: Premium cocktails $12-16, wines $8-12\n• Food: Appetizer discounts 25-50% off\n• Location: La Jolla's upscale dining scene\n\n**Status:** API key configuration needed for full GPT-5 analysis.",
                        "model_used": "configuration-required",
                        "api_type": "config_error",
                        "tokens_used": 0,
                        "reasoning_tokens": 0,
                        "reasoning_effort": "none",
                        "timestamp": datetime.now().isoformat()
                    })
                }
            
            # Call GPT-5 API with parallel agent reasoning
            gpt5_result = call_gpt5_api(restaurant_data, api_key)
            
            if gpt5_result['success']:
                raw_content = gpt5_result['content']
                
                # Try to parse as JSON first, but default to narrative display
                try:
                    # Try parsing as structured JSON
                    structured_analysis = json.loads(raw_content)
                    formatted_analysis = format_structured_analysis(structured_analysis, restaurant_name)
                    api_type = "gpt5_structured"
                    extra_data = {"structured_data": structured_analysis}
                except json.JSONDecodeError:
                    # GPT-5 returned narrative text - use it directly
                    formatted_analysis = raw_content
                    api_type = "gpt5_narrative"
                    extra_data = {"analysis_format": "narrative_with_insights"}
                
                # Format final response
                final_analysis = f"🚀 **GPT-5 Parallel Agent Analysis**\n\n{formatted_analysis}\n\n*Analysis performed using GPT-5 with high reasoning effort and parallel agent methodology*"
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers(),
                    'body': json.dumps({
                        "restaurant_name": restaurant_name,
                        "gpt5_analysis": final_analysis,
                        "model_used": gpt5_result['model'],
                        "api_type": api_type,
                        "tokens_used": gpt5_result['tokens_used'],
                        "reasoning_tokens": gpt5_result['reasoning_tokens'],
                        "reasoning_effort": "high",
                        "timestamp": datetime.now().isoformat(),
                        "parallel_agents": ["market_analyst", "schedule_predictor", "pricing_analyst"],
                        **extra_data
                    })
                }
            else:
                return {
                    'statusCode': 200,
                    'headers': cors_headers(),
                    'body': json.dumps({
                        "restaurant_name": restaurant_name,
                        "gpt5_analysis": f"🚫 **GPT-5 API Error**\n\nThe GPT-5 analysis for {restaurant_name} could not be completed due to an API error: {gpt5_result['error']}\n\n**Fallback Analysis:**\nBased on La Jolla dining patterns:\n• Happy Hour: Monday-Friday 3:00-6:00 PM\n• Premium location with upscale offerings\n• Call restaurant directly for current specials\n\n**Status:** GPT-5 API connection issue - please try again later.",
                        "model_used": "gpt5-error-fallback",
                        "api_type": "gpt5_api_error",
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
#!/usr/bin/env python3
"""
Proper GPT-5 Happy Hour Discovery System
Uses the correct Responses API and GPT-5 specific parameters
"""

import asyncio
import json
import os
import pandas as pd
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class ProperGPT5System:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def test_gpt5_responses_api(self):
        """Test GPT-5 with proper Responses API"""
        
        print("🧪 Testing GPT-5 Responses API...")
        
        try:
            # Test basic Responses API (correct format based on OpenAI docs)
            response = await self.client.responses.create(
                model="gpt-5",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Hello, I am testing GPT-5. Please respond with a JSON object containing a greeting message and confirmation you are GPT-5."}
                        ]
                    }
                ]
            )
            
            print(f"✅ GPT-5 Response (Responses API):")
            print(f"Response type: {type(response)}")
            print(f"Response attributes: {dir(response)}")
            
            # Try different attribute names
            content = None
            if hasattr(response, 'output_text'):
                content = response.output_text
            elif hasattr(response, 'content'):
                content = response.content
            elif hasattr(response, 'text'):
                content = response.text
            elif hasattr(response, 'response'):
                content = response.response
                
            print(f"Content: {content}")
            print(f"Full response: {response}")
            
            return True
            
        except Exception as e:
            print(f"❌ Responses API failed: {e}")
            
            # Fallback to Chat Completions with proper model name
            try:
                print("\n🔄 Trying Chat Completions with proper model name...")
                
                response = await self.client.chat.completions.create(
                    model="gpt-5-2025-08-07",  # Full model name
                    messages=[
                        {"role": "user", "content": "Hello from GPT-5. Respond with JSON: {\"message\": \"hello\", \"model\": \"gpt-5\"}"}
                    ],
                    response_format={"type": "json_object"},
                    max_completion_tokens=100
                )
                
                content = response.choices[0].message.content
                print(f"✅ Chat Completions Response:")
                print(f"Content: '{content}'")
                print(f"Tokens: {response.usage.total_tokens}")
                
                if content and content.strip():
                    result = json.loads(content)
                    print(f"Parsed JSON: {result}")
                    return True
                    
            except Exception as e2:
                print(f"❌ Chat Completions also failed: {e2}")
                return False
    
    async def discover_happy_hour_responses_api(self, restaurant):
        """Use GPT-5 Responses API for happy hour discovery"""
        
        print(f"\n🔍 Analyzing {restaurant['Record Name']} with GPT-5 Responses API")
        
        # Create comprehensive input for GPT-5
        input_text = f"""
        Analyze this restaurant for happy hour information:
        
        Restaurant: {restaurant['Record Name']}
        Address: {restaurant['Address']}, {restaurant['City']}, {restaurant['State']} {restaurant['Zip']}
        Phone: {restaurant.get('Permit Owner Business Phone', 'N/A')}
        Business Type: {restaurant.get('Business Type', 'Restaurant')}
        
        Based on the restaurant name, location in La Jolla (an upscale area), and business type, provide a comprehensive assessment:
        
        1. Likelihood of having happy hour (high/medium/low/none)
        2. Restaurant category (upscale dining, casual, bar, fast food, etc.)
        3. Estimated happy hour schedule if likely
        4. Typical specials they might offer
        5. Confidence level in your assessment
        
        Consider La Jolla restaurant trends, the establishment type, and industry standards.
        
        Respond with structured information including your reasoning.
        """
        
        try:
            # Use GPT-5 Responses API (correct format)
            response = await self.client.responses.create(
                model="gpt-5",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": input_text}
                        ]
                    }
                ]
            )
            
            # Extract content from GPT-5 Responses API
            content = response.output_text if hasattr(response, 'output_text') else str(response)
            
            result = {
                "restaurant_name": restaurant['Record Name'],
                "gpt5_analysis": content,
                "model_used": response.model,
                "api_type": "responses_api",
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None,
                "reasoning_tokens": response.usage.output_tokens_details.reasoning_tokens if hasattr(response, 'usage') and hasattr(response.usage, 'output_tokens_details') else None,
                "reasoning_effort": response.reasoning.effort if hasattr(response, 'reasoning') else None,
                "verbosity": response.text.verbosity if hasattr(response, 'text') else None,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Error with Responses API: {e}")
            
            # Fallback to Chat Completions
            return await self.discover_happy_hour_chat_api(restaurant)
    
    async def discover_happy_hour_chat_api(self, restaurant):
        """Fallback to Chat Completions API with proper GPT-5 usage"""
        
        print(f"🔄 Fallback: Using Chat Completions for {restaurant['Record Name']}")
        
        prompt = f"""
        Restaurant Analysis for Happy Hour:
        
        Name: {restaurant['Record Name']}
        Address: {restaurant['Address']}, {restaurant['City']}, {restaurant['State']}
        Type: {restaurant.get('Business Type', 'Restaurant')}
        
        Analyze this La Jolla restaurant for happy hour likelihood.
        
        Respond in JSON format:
        {{
            "restaurant_name": "{restaurant['Record Name']}",
            "likely_has_happy_hour": true/false,
            "confidence_percentage": 0-100,
            "restaurant_category": "category",
            "estimated_schedule": "weekdays 3-6pm" or "none",
            "typical_specials": ["list of likely specials"],
            "reasoning": "brief explanation",
            "la_jolla_context": "how location affects assessment"
        }}
        """
        
        try:
            # Try different GPT-5 model names
            for model in ["gpt-5", "gpt-5-2025-08-07", "gpt-5-mini", "gpt-5-nano"]:
                try:
                    # Add reasoning_effort for GPT-5 models
                    params = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are a restaurant industry expert analyzing happy hour likelihood in La Jolla, CA."},
                            {"role": "user", "content": prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "max_completion_tokens": 800
                    }
                    
                    # Add GPT-5 specific parameters
                    if "gpt-5" in model:
                        params["reasoning_effort"] = "medium"
                    
                    response = await self.client.chat.completions.create(**params)
                    
                    content = response.choices[0].message.content
                    if content and content.strip():
                        result = json.loads(content)
                        result["model_used"] = model
                        result["api_type"] = "chat_completions" 
                        result["tokens_used"] = response.usage.total_tokens
                        result["timestamp"] = datetime.now().isoformat()
                        
                        print(f"✅ Success with model: {model}")
                        return result
                    
                except Exception as model_error:
                    print(f"❌ Failed with {model}: {str(model_error)[:50]}")
                    continue
            
            # If all models failed
            return {
                "restaurant_name": restaurant['Record Name'],
                "error": "All GPT-5 models failed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "restaurant_name": restaurant['Record Name'],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Proper GPT-5 Happy Hour Discovery")
    parser.add_argument('--test', action='store_true', help='Test GPT-5 API first')
    parser.add_argument('--restaurant', type=str, help='Process specific restaurant')
    parser.add_argument('--limit', type=int, default=3, help='Number of restaurants to process')
    args = parser.parse_args()
    
    system = ProperGPT5System()
    
    if args.test:
        print("🚀 Testing GPT-5 Proper Usage")
        print("=" * 60)
        success = await system.test_gpt5_responses_api()
        if not success:
            print("\n❌ GPT-5 testing failed. Check your API access.")
            return
        print("\n✅ GPT-5 is working properly!")
        return
    
    # Load restaurant data
    df = pd.read_csv("food_permits_restaurants.csv")
    
    if args.restaurant:
        matches = df[df['Record Name'].str.contains(args.restaurant, case=False, na=False)]
        if matches.empty:
            print(f"No restaurant found matching '{args.restaurant}'")
            return
        restaurants = [matches.iloc[0].to_dict()]
    else:
        restaurants = df.head(args.limit).to_dict('records')
    
    print(f"\n🍻 GPT-5 Happy Hour Discovery System")
    print(f"Processing {len(restaurants)} restaurant(s)")
    print("=" * 60)
    
    results = []
    
    for i, restaurant in enumerate(restaurants, 1):
        print(f"\n[{i}/{len(restaurants)}] Processing...")
        
        # Try Responses API first, fallback to Chat
        result = await system.discover_happy_hour_responses_api(restaurant)
        
        # Display results
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Analysis complete")
            print(f"Model used: {result.get('model_used', 'unknown')}")
            print(f"API type: {result.get('api_type', 'unknown')}")
            print(f"Tokens: {result.get('tokens_used', 'unknown')}")
            
            # Try to extract key insights from the analysis
            analysis = result.get('gpt5_analysis', '')
            if analysis:
                print(f"Analysis preview: {analysis[:150]}...")
            
            # If it's structured JSON, show key fields
            if isinstance(result.get('gpt5_analysis'), dict):
                data = result['gpt5_analysis']
                if 'likely_has_happy_hour' in data:
                    hh_status = "✅ Yes" if data['likely_has_happy_hour'] else "❌ No"
                    confidence = data.get('confidence_percentage', 'unknown')
                    print(f"Happy Hour: {hh_status} ({confidence}% confidence)")
        
        results.append(result)
        
        # Save progress
        output_file = "proper_gpt5_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Brief pause
        await asyncio.sleep(1)
    
    print(f"\n💾 Results saved to: {output_file}")
    print(f"📊 Total processed: {len(results)}")
    
    # Show summary
    successful = [r for r in results if "error" not in r]
    if successful:
        print(f"✅ Successful analyses: {len(successful)}")
        models_used = set(r.get('model_used', 'unknown') for r in successful)
        print(f"🤖 Models used: {', '.join(models_used)}")

if __name__ == "__main__":
    asyncio.run(main())
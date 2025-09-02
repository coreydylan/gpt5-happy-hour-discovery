#!/usr/bin/env python3
"""
GPT-5 Happy Hour Discovery with Built-in Tools
Leverages GPT-5's web search and parallel tool execution
"""

import asyncio
import json
import os
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def discover_happy_hour_with_tools():
    """Use GPT-5 with tools to find happy hour information"""
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Test restaurant
    restaurant = {
        "name": "BARBARELLA RESTAURANT",
        "address": "2171 AVENIDA DE LA PLAYA, LA JOLLA, CA 92037",
        "phone": "858-242-2589"
    }
    
    print(f"\n🔍 GPT-5 Happy Hour Discovery with Web Search")
    print(f"Restaurant: {restaurant['name']}")
    print(f"Address: {restaurant['address']}")
    print("-" * 60)
    
    # Define the web search tool for GPT-5
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    # Comprehensive prompt for GPT-5
    prompt = f"""
    Find comprehensive happy hour information for this restaurant using web search:
    
    Restaurant: {restaurant['name']}
    Address: {restaurant['address']}
    Phone: {restaurant['phone']}
    
    Perform the following searches:
    1. Search for "{restaurant['name']} happy hour La Jolla"
    2. Search for "{restaurant['name']} drink specials"
    3. Check Yelp, Google, and the restaurant's website
    
    Extract and return as JSON:
    - has_happy_hour: boolean (true/false/null if uncertain)
    - schedule: array of objects with day and time ranges
    - drinks: array of drink specials with prices
    - food: array of food specials with prices
    - sources: array of URLs where information was found
    - confidence_score: 0-1 rating
    - verification_status: "verified", "likely", "uncertain", or "no_data"
    - notes: any additional context
    
    Use parallel tool calls to search multiple sources simultaneously for efficiency.
    """
    
    try:
        # Call GPT-5 with tools enabled
        response = await client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a restaurant information specialist. Use web search to find accurate, current happy hour information. Return structured JSON data."
                },
                {"role": "user", "content": prompt}
            ],
            tools=tools,
            tool_choice="auto",  # Let GPT-5 decide when to use tools
            parallel_tool_calls=True,  # GPT-5 parallel execution
            response_format={"type": "json_object"},
            max_completion_tokens=3000
        )
        
        # Handle tool calls if any
        message = response.choices[0].message
        
        if message.tool_calls:
            print(f"\n🔧 GPT-5 made {len(message.tool_calls)} tool calls:")
            for tool_call in message.tool_calls:
                print(f"  - {tool_call.function.name}: {json.loads(tool_call.function.arguments)['query']}")
            
            # In a real implementation, you would execute these tool calls
            # and feed the results back to GPT-5 for final processing
            print("\n⚠️  Note: Tool execution would happen here in production")
            print("GPT-5 would search these queries and return structured results")
        
        # Parse the final response
        if message.content:
            result = json.loads(message.content)
            
            print("\n✅ GPT-5 Response:")
            print(json.dumps(result, indent=2))
            
            # Save to file
            output_file = f"gpt5_tools_{restaurant['name'].replace(' ', '_')}.json"
            with open(output_file, 'w') as f:
                json.dump({
                    "restaurant": restaurant,
                    "gpt5_response": result,
                    "tool_calls": [
                        {
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments)
                        } for tc in message.tool_calls
                    ] if message.tool_calls else [],
                    "timestamp": datetime.now().isoformat(),
                    "model": "gpt-5",
                    "tokens_used": response.usage.total_tokens
                }, f, indent=2)
            
            print(f"\n💾 Results saved to: {output_file}")
            print(f"📊 Tokens used: {response.usage.total_tokens}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

async def test_gpt5_models():
    """Test different GPT-5 model variants"""
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    models = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
    
    print("\n🧪 Testing GPT-5 Model Variants")
    print("=" * 60)
    
    for model in models:
        try:
            print(f"\nTesting {model}...")
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": "Return a JSON object with a single field 'model' containing your model name."}
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=100
            )
            
            result = json.loads(response.choices[0].message.content)
            print(f"✅ {model} working: {result}")
            print(f"   Tokens: {response.usage.total_tokens}")
            
        except Exception as e:
            print(f"❌ {model} error: {str(e)[:100]}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    print("\n🚀 GPT-5 Happy Hour Discovery System")
    print("Testing GPT-5's advanced capabilities")
    
    # Test model availability first
    asyncio.run(test_gpt5_models())
    
    # Then test with tools
    asyncio.run(discover_happy_hour_with_tools())
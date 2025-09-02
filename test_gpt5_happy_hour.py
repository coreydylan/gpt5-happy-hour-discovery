#!/usr/bin/env python3
"""
Simplified GPT-5 Happy Hour Discovery Test
Tests the system with a single restaurant using GPT-5's capabilities
"""

import asyncio
import json
import os
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_gpt5_happy_hour():
    """Test GPT-5's ability to find happy hour information"""
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Test restaurant
    restaurant = {
        "name": "BARBARELLA RESTAURANT",
        "address": "2171 AVENIDA DE LA PLAYA, LA JOLLA, CA 92037",
        "phone": "858-242-2589"
    }
    
    print(f"\n🔍 Testing GPT-5 Happy Hour Discovery")
    print(f"Restaurant: {restaurant['name']}")
    print(f"Address: {restaurant['address']}")
    print("-" * 60)
    
    # Construct a comprehensive prompt for GPT-5
    prompt = f"""
    Find comprehensive happy hour information for this restaurant:
    
    Restaurant: {restaurant['name']}
    Address: {restaurant['address']}
    Phone: {restaurant['phone']}
    
    Search for and provide:
    1. Happy hour schedule (days and times)
    2. Drink specials and prices
    3. Food specials and prices
    4. Any restrictions or special conditions
    5. Source URLs where you found this information
    
    Return the information as a JSON object with these fields:
    - has_happy_hour: boolean
    - schedule: array of day/time objects
    - drinks: array of drink specials
    - food: array of food specials
    - sources: array of source URLs
    - confidence_score: 0-1 rating of data reliability
    - notes: any additional relevant information
    
    If you cannot find information, return has_happy_hour: null with explanation in notes.
    """
    
    try:
        # Call GPT-5 with JSON mode (using GPT-5 specific parameters)
        response = await client.chat.completions.create(
            model="gpt-5",  # Using GPT-5
            messages=[
                {
                    "role": "system", 
                    "content": "You are a restaurant information specialist. Search for and extract happy hour information. Return valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            # GPT-5 only supports default temperature (1)
            max_completion_tokens=2000  # GPT-5 uses max_completion_tokens
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        
        print("\n✅ GPT-5 Response:")
        print(json.dumps(result, indent=2))
        
        # Save to file
        output_file = f"test_happy_hour_{restaurant['name'].replace(' ', '_')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "restaurant": restaurant,
                "gpt5_response": result,
                "timestamp": datetime.now().isoformat(),
                "model": "gpt-5",
                "tokens_used": response.usage.total_tokens
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print(f"📊 Tokens used: {response.usage.total_tokens}")
        
        # Display summary
        if result.get('has_happy_hour') is True:
            print(f"\n🍻 Happy Hour Found!")
            if 'schedule' in result:
                print("Schedule:", result['schedule'])
            if 'confidence_score' in result:
                print(f"Confidence: {result['confidence_score']:.0%}")
        elif result.get('has_happy_hour') is False:
            print(f"\n❌ No Happy Hour")
        else:
            print(f"\n❓ Unable to determine")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible issues:")
        print("1. Check your OpenAI API key is valid")
        print("2. Ensure you have access to GPT-5 models")
        print("3. Check your API quota and billing")

if __name__ == "__main__":
    asyncio.run(test_gpt5_happy_hour())
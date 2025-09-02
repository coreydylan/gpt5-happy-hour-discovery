#!/usr/bin/env python3
"""
Simple Working GPT-5 Happy Hour System
Guaranteed to work with GPT-5
"""

import asyncio
import json
import os
import pandas as pd
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class SimpleHappyHourFinder:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def analyze_restaurant(self, name, address, phone=None):
        """Simple restaurant happy hour analysis"""
        
        prompt = f"""Analyze this restaurant for happy hour likelihood:

Restaurant: {name}
Address: {address}
Phone: {phone or 'N/A'}

Based on the name, type, and location, assess:
1. Does this restaurant likely have happy hour? (yes/no/maybe)
2. What type of establishment is this?
3. What would be typical happy hour times?
4. What specials might they offer?

Respond in JSON format with these exact fields:
- restaurant_name
- likely_has_happy_hour (true/false/null)
- restaurant_type 
- confidence (0-100)
- estimated_times
- reasoning

Example response:
{{"restaurant_name": "Example Bar", "likely_has_happy_hour": true, "restaurant_type": "sports bar", "confidence": 80, "estimated_times": "3-6pm weekdays", "reasoning": "Sports bars typically offer happy hour specials"}}"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=500
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
                result["tokens_used"] = response.usage.total_tokens
                return result
            else:
                return {"error": "Empty response", "restaurant_name": name}
                
        except Exception as e:
            return {"error": str(e), "restaurant_name": name}

async def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--restaurant', help='Restaurant name to search for')
    parser.add_argument('--limit', type=int, default=5, help='Number of restaurants')
    args = parser.parse_args()
    
    finder = SimpleHappyHourFinder()
    
    # Load restaurants
    df = pd.read_csv("food_permits_restaurants.csv")
    
    if args.restaurant:
        # Find specific restaurant
        matches = df[df['Record Name'].str.contains(args.restaurant, case=False, na=False)]
        if matches.empty:
            print(f"No restaurant found matching '{args.restaurant}'")
            return
        restaurants = matches.head(1).to_dict('records')
    else:
        # Process multiple
        restaurants = df.head(args.limit).to_dict('records')
    
    print(f"\n🔍 Analyzing {len(restaurants)} restaurant(s) with GPT-5")
    print("="*60)
    
    results = []
    for i, restaurant in enumerate(restaurants, 1):
        name = restaurant['Record Name']
        address = f"{restaurant['Address']}, {restaurant['City']}"
        phone = restaurant.get('Permit Owner Business Phone')
        
        print(f"\n[{i}] {name}")
        print(f"    {address}")
        
        result = await finder.analyze_restaurant(name, address, phone)
        
        if "error" in result:
            print(f"    ❌ Error: {result['error']}")
        else:
            has_hh = result.get('likely_has_happy_hour')
            confidence = result.get('confidence', 0)
            
            if has_hh is True:
                print(f"    ✅ Likely has happy hour ({confidence}% confidence)")
            elif has_hh is False:
                print(f"    ❌ Unlikely to have happy hour ({confidence}% confidence)")
            else:
                print(f"    ❓ Uncertain ({confidence}% confidence)")
            
            print(f"    🏷️  Type: {result.get('restaurant_type', 'Unknown')}")
            print(f"    ⏰ Est. times: {result.get('estimated_times', 'N/A')}")
            print(f"    💭 {result.get('reasoning', 'No reasoning provided')[:80]}...")
            
            if 'tokens_used' in result:
                print(f"    📊 Tokens: {result['tokens_used']}")
        
        results.append(result)
        
        # Brief pause
        await asyncio.sleep(0.5)
    
    # Save results
    output_file = "simple_happy_hour_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    successful = [r for r in results if "error" not in r]
    if successful:
        likely_yes = sum(1 for r in successful if r.get('likely_has_happy_hour') is True)
        likely_no = sum(1 for r in successful if r.get('likely_has_happy_hour') is False)
        uncertain = sum(1 for r in successful if r.get('likely_has_happy_hour') is None)
        
        print(f"Likely have happy hour: {likely_yes}")
        print(f"Unlikely to have happy hour: {likely_no}")
        print(f"Uncertain: {uncertain}")
        
        avg_confidence = sum(r.get('confidence', 0) for r in successful) / len(successful)
        print(f"Average confidence: {avg_confidence:.0f}%")
        
        # Show high confidence results
        high_confidence = [r for r in successful if r.get('confidence', 0) > 70 and r.get('likely_has_happy_hour') is True]
        if high_confidence:
            print(f"\n🍺 High confidence happy hour spots:")
            for r in high_confidence:
                print(f"  • {r['restaurant_name']} ({r.get('confidence', 0)}%)")
                print(f"    Times: {r.get('estimated_times', 'TBD')}")
    
    print(f"\n💾 Results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
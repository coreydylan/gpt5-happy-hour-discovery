#!/usr/bin/env python3
"""
Working GPT-5 Happy Hour Discovery System
This version properly uses GPT-5 to find happy hour information
"""

import asyncio
import json
import os
import pandas as pd
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Load environment variables
load_dotenv()

class WorkingHappyHourSystem:
    """Simplified but working happy hour discovery using GPT-5"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def find_happy_hour(self, restaurant: Dict) -> Dict:
        """Find happy hour info using GPT-5's capabilities"""
        
        # Create a comprehensive prompt that GPT-5 can work with
        prompt = f"""
        You are researching happy hour information for this restaurant:
        
        Name: {restaurant.get('Record Name', 'Unknown')}
        Address: {restaurant.get('Address', '')}, {restaurant.get('City', '')}, {restaurant.get('State', '')} {restaurant.get('Zip', '')}
        Phone: {restaurant.get('Permit Owner Business Phone', 'Unknown')}
        
        Based on your knowledge and the restaurant details provided, determine:
        
        1. Whether this restaurant likely has a happy hour (consider the type of establishment)
        2. Typical happy hour schedule if they have one (use industry standards for similar restaurants)
        3. Common happy hour offerings (drinks and food specials typical for this type of venue)
        4. Confidence level in your assessment
        
        Consider factors like:
        - Restaurant type (bar, casual dining, upscale, etc.)
        - Location (La Jolla is an upscale area with many happy hours)
        - Common practices for similar establishments
        
        Return a comprehensive JSON object with this structure:
        {{
            "restaurant_name": "name",
            "has_happy_hour": true/false/null,
            "confidence_score": 0.0-1.0,
            "verification_status": "likely"/"uncertain"/"estimated",
            "schedule": [
                {{
                    "day": "monday",
                    "start_time": "15:00",
                    "end_time": "18:00",
                    "notes": "any special notes"
                }}
            ],
            "estimated_specials": {{
                "drinks": [
                    {{
                        "item": "House Wine",
                        "estimated_price": "$5-7",
                        "regular_price": "$10-12",
                        "category": "wine"
                    }}
                ],
                "food": [
                    {{
                        "item": "Appetizers",
                        "estimated_discount": "50% off or $5-8",
                        "category": "appetizer"
                    }}
                ]
            }},
            "reasoning": "Brief explanation of your assessment",
            "search_suggestions": [
                "Specific searches that would verify this information"
            ],
            "likelihood_explanation": "Why this restaurant would/wouldn't have happy hour"
        }}
        
        Be realistic and use industry knowledge. For example:
        - Upscale restaurants often have bar/lounge happy hours
        - Mexican restaurants usually have margarita specials
        - Coffee shops typically don't have happy hours
        - Hotel restaurants often have happy hours
        - Fast food chains rarely have happy hours
        """
        
        try:
            # Call GPT-5 for analysis
            response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a restaurant industry expert with deep knowledge of happy hour trends and practices. Provide realistic assessments based on restaurant type and location."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error processing {restaurant.get('Record Name', 'Unknown')}: {e}")
            return {
                "restaurant_name": restaurant.get('Record Name', 'Unknown'),
                "has_happy_hour": None,
                "confidence_score": 0,
                "error": str(e)
            }
    
    async def process_restaurants(self, csv_file: str, limit: Optional[int] = None):
        """Process multiple restaurants from CSV"""
        
        # Read CSV
        df = pd.read_csv(csv_file)
        if limit:
            df = df.head(limit)
        
        restaurants = df.to_dict('records')
        results = []
        
        print(f"\n🍻 Processing {len(restaurants)} restaurants using GPT-5")
        print("=" * 60)
        
        for i, restaurant in enumerate(restaurants, 1):
            print(f"\n[{i}/{len(restaurants)}] {restaurant['Record Name']}")
            
            # Get analysis from GPT-5
            result = await self.find_happy_hour(restaurant)
            
            # Display summary
            if result.get('has_happy_hour') is True:
                print(f"  ✅ Likely has happy hour (confidence: {result.get('confidence_score', 0):.0%})")
                if 'schedule' in result and result['schedule']:
                    print(f"  📅 Estimated schedule: {result['schedule'][0].get('start_time', 'TBD')} - {result['schedule'][0].get('end_time', 'TBD')}")
            elif result.get('has_happy_hour') is False:
                print(f"  ❌ Unlikely to have happy hour")
            else:
                print(f"  ❓ Unable to determine")
            
            if 'reasoning' in result:
                print(f"  💭 {result['reasoning'][:100]}...")
            
            results.append(result)
            
            # Save progress
            with open('working_happy_hour_results.json', 'w') as f:
                json.dump(results, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        likely_yes = sum(1 for r in results if r.get('has_happy_hour') is True)
        likely_no = sum(1 for r in results if r.get('has_happy_hour') is False)
        uncertain = sum(1 for r in results if r.get('has_happy_hour') is None)
        
        print(f"Likely have happy hour: {likely_yes}")
        print(f"Unlikely to have happy hour: {likely_no}")
        print(f"Uncertain: {uncertain}")
        
        avg_confidence = sum(r.get('confidence_score', 0) for r in results) / len(results)
        print(f"Average confidence: {avg_confidence:.0%}")
        
        # Show examples of likely happy hour spots
        print("\n🍺 Restaurants likely to have happy hour:")
        for r in results:
            if r.get('has_happy_hour') is True and r.get('confidence_score', 0) > 0.7:
                print(f"  • {r['restaurant_name']} ({r.get('confidence_score', 0):.0%} confidence)")
                if 'estimated_specials' in r and 'drinks' in r['estimated_specials']:
                    drinks = r['estimated_specials']['drinks']
                    if drinks:
                        print(f"    Likely specials: {drinks[0]['item']} {drinks[0].get('estimated_price', 'TBD')}")
        
        print(f"\n💾 Results saved to: working_happy_hour_results.json")
        
        return results

async def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Working Happy Hour Discovery")
    parser.add_argument('--limit', type=int, help='Number of restaurants to process')
    parser.add_argument('--restaurant', type=str, help='Process single restaurant by name')
    args = parser.parse_args()
    
    system = WorkingHappyHourSystem()
    
    if args.restaurant:
        # Process single restaurant
        df = pd.read_csv("food_permits_restaurants.csv")
        matches = df[df['Record Name'].str.contains(args.restaurant, case=False, na=False)]
        
        if matches.empty:
            print(f"No restaurant found matching '{args.restaurant}'")
            return
        
        restaurant = matches.iloc[0].to_dict()
        print(f"\n🔍 Analyzing: {restaurant['Record Name']}")
        print(f"📍 Location: {restaurant['Address']}, {restaurant['City']}")
        
        result = await system.find_happy_hour(restaurant)
        
        print("\n" + "=" * 60)
        print("📋 ANALYSIS RESULTS")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        
        # Save to file
        with open(f"analysis_{restaurant['Record Name'].replace(' ', '_')}.json", 'w') as f:
            json.dump(result, f, indent=2)
        
    else:
        # Process multiple
        await system.process_restaurants(
            "food_permits_restaurants.csv",
            limit=args.limit or 10
        )

if __name__ == "__main__":
    asyncio.run(main())
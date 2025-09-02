#!/usr/bin/env python3
"""
Runner script for Happy Hour Discovery System
Provides a simple interface to process restaurants and generate comprehensive happy hour data
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from happy_hour_discovery_system import (
    HappyHourDiscoverySystem,
    process_restaurants_batch,
    HappyHourData
)

def setup_environment():
    """Setup environment and check requirements"""
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set it using: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Check for input file
    if not Path("food_permits_restaurants.csv").exists():
        print("❌ Error: food_permits_restaurants.csv not found")
        print("Please ensure the CSV file is in the current directory")
        sys.exit(1)
    
    return api_key

def print_summary(results_file: str):
    """Print summary statistics of the results"""
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    total = len(results)
    has_happy_hour = sum(1 for r in results if r.get('has_happy_hour') == True)
    no_happy_hour = sum(1 for r in results if r.get('has_happy_hour') == False)
    uncertain = sum(1 for r in results if r.get('has_happy_hour') is None)
    needs_review = sum(1 for r in results if r.get('requires_human_review', False))
    
    print("\n" + "="*60)
    print("📊 HAPPY HOUR DISCOVERY RESULTS SUMMARY")
    print("="*60)
    print(f"Total restaurants processed: {total}")
    print(f"✅ Has happy hour: {has_happy_hour} ({has_happy_hour/total*100:.1f}%)")
    print(f"❌ No happy hour: {no_happy_hour} ({no_happy_hour/total*100:.1f}%)")
    print(f"❓ Uncertain: {uncertain} ({uncertain/total*100:.1f}%)")
    print(f"⚠️  Needs human review: {needs_review} ({needs_review/total*100:.1f}%)")
    
    # Calculate average scores
    confidence_scores = [r.get('confidence_score', 0) for r in results if 'confidence_score' in r]
    completeness_scores = [r.get('data_completeness_score', 0) for r in results if 'data_completeness_score' in r]
    
    if confidence_scores:
        print(f"\n📈 Average confidence score: {sum(confidence_scores)/len(confidence_scores):.2f}")
    if completeness_scores:
        print(f"📈 Average completeness score: {sum(completeness_scores)/len(completeness_scores):.2f}")
    
    # Show examples of high-quality results
    high_quality = [r for r in results if r.get('confidence_score', 0) > 0.8 and r.get('data_completeness_score', 0) > 0.8]
    if high_quality:
        print(f"\n🌟 High-quality results ({len(high_quality)} restaurants with >80% confidence & completeness):")
        for r in high_quality[:5]:  # Show first 5
            print(f"  - {r['restaurant_name']}: {r.get('schedule_notes', 'Full schedule available')}")
    
    print("\n" + "="*60)

async def run_single_restaurant(api_key: str, restaurant_name: str):
    """Process a single restaurant by name"""
    import pandas as pd
    
    df = pd.read_csv("food_permits_restaurants.csv")
    
    # Find restaurant by name (case-insensitive)
    matches = df[df['Record Name'].str.contains(restaurant_name, case=False, na=False)]
    
    if matches.empty:
        print(f"❌ No restaurant found matching '{restaurant_name}'")
        return
    
    if len(matches) > 1:
        print(f"Found {len(matches)} matches:")
        for idx, row in matches.iterrows():
            print(f"  {idx}: {row['Record Name']} - {row['Address']}")
        selection = input("Enter row number to process (or 'all' for all matches): ")
        
        if selection.lower() == 'all':
            restaurants = matches.to_dict('records')
        else:
            try:
                restaurants = [matches.loc[int(selection)].to_dict()]
            except:
                print("Invalid selection")
                return
    else:
        restaurants = matches.to_dict('records')
    
    print(f"\n🔍 Processing {len(restaurants)} restaurant(s)...")
    
    async with HappyHourDiscoverySystem(api_key, max_parallel_agents=10) as system:
        for restaurant in restaurants:
            print(f"\n📍 {restaurant['Record Name']}")
            print(f"   {restaurant['Address']}, {restaurant['City']}")
            print("   Discovering happy hour information...")
            
            result = await system.discover_happy_hour(restaurant)
            
            # Save individual result
            output_file = f"happy_hour_{restaurant['Record Name'].replace(' ', '_').replace('/', '_')}.json"
            with open(output_file, 'w') as f:
                json.dump(result.model_dump(), f, indent=2, default=str)
            
            # Print results
            print(f"\n   ✅ Results:")
            print(f"   - Has Happy Hour: {result.has_happy_hour}")
            print(f"   - Confidence: {result.confidence_score:.2%}")
            print(f"   - Completeness: {result.data_completeness_score:.2%}")
            
            if result.schedule:
                print("   - Schedule:")
                for day in result.schedule:
                    if day.is_available:
                        times = ", ".join([f"{ts.start_time}-{ts.end_time}" for ts in day.time_slots])
                        print(f"     {day.day.value.capitalize()}: {times}")
            
            if result.menu and result.menu.drinks:
                print(f"   - Drink specials: {len(result.menu.drinks)} items")
            
            if result.menu and result.menu.food:
                print(f"   - Food specials: {len(result.menu.food)} items")
            
            if result.sources:
                print(f"   - Sources: {len(result.sources)} verified sources")
                for source in result.sources[:3]:  # Show first 3
                    print(f"     • {source.domain} (confidence: {source.reliability_score:.2f})")
            
            if result.requires_human_review:
                print(f"   ⚠️  Requires review: {', '.join(result.human_review_reasons)}")
            
            print(f"\n   💾 Saved to: {output_file}")

async def main():
    parser = argparse.ArgumentParser(description="Happy Hour Discovery System")
    parser.add_argument('--batch-size', type=int, default=5, 
                       help='Number of restaurants to process in parallel (default: 5)')
    parser.add_argument('--limit', type=int, 
                       help='Limit number of restaurants to process')
    parser.add_argument('--restaurant', type=str,
                       help='Process a single restaurant by name')
    parser.add_argument('--output', type=str, default='happy_hour_results.json',
                       help='Output file name (default: happy_hour_results.json)')
    parser.add_argument('--start-from', type=int, default=0,
                       help='Start processing from row N in CSV (default: 0)')
    
    args = parser.parse_args()
    
    print("\n🍻 HAPPY HOUR DISCOVERY SYSTEM 🍻")
    print("="*60)
    print("Leveraging GPT-5's advanced capabilities:")
    print("  • Parallel agent deployment")
    print("  • Structured JSON outputs")
    print("  • Multi-source verification")
    print("  • Intelligent data aggregation")
    print("="*60)
    
    api_key = setup_environment()
    
    if args.restaurant:
        # Process single restaurant
        await run_single_restaurant(api_key, args.restaurant)
    else:
        # Process batch
        import pandas as pd
        df = pd.read_csv("food_permits_restaurants.csv")
        
        # Apply start and limit
        if args.start_from > 0:
            df = df.iloc[args.start_from:]
        if args.limit:
            df = df.head(args.limit)
        
        # Save filtered CSV temporarily
        temp_csv = "temp_filtered_restaurants.csv"
        df.to_csv(temp_csv, index=False)
        
        print(f"\n📋 Processing {len(df)} restaurants")
        print(f"   Batch size: {args.batch_size}")
        print(f"   Output file: {args.output}")
        print(f"   Estimated time: {len(df) * 10 / args.batch_size:.1f} seconds")
        print("\nStarting processing...\n")
        
        try:
            results = await process_restaurants_batch(
                csv_file=temp_csv,
                output_file=args.output,
                api_key=api_key,
                batch_size=args.batch_size
            )
            
            # Print summary
            print_summary(args.output)
            
        finally:
            # Clean up temp file
            if Path(temp_csv).exists():
                Path(temp_csv).unlink()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
#!/usr/bin/env python3
"""
Debug Supabase import issues
"""
import csv
import json
import urllib.request
import urllib.parse

def test_single_insert():
    """Test a single restaurant insert to debug the issue"""
    
    # Read one restaurant from the CSV
    with open('archive/true_happy_hour_venues.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        row = next(reader)
        print("Raw CSV row:")
        for key, value in row.items():
            print(f"  {key}: {value}")
    
    # Format the data
    venue_data = {
        "name": row.get("DBA NAME", "").strip().upper(),
        "address": row.get("ADDRESS", "").strip(),
        "city": row.get("CITY", "").strip().upper(),
        "state": row.get("STATE", "").strip().upper(),
        "country": "US",
        "phone_e164": format_phone(row.get("BUSINESS PHONE", "")),
        "postal_code": row.get("ZIP", "").strip()
    }
    
    print("\nFormatted venue data:")
    print(json.dumps(venue_data, indent=2))
    
    # Try to insert
    supabase_url = "https://vnnplotrwbtjtopknxgl.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZubnBsb3Ryd2J0anRvcGtueGdsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Njc4NDc1OCwiZXhwIjoyMDcyMzYwNzU4fQ.qFZl7LLGqc9CmpIfPKy8bNyHoexCB_sdre-hc08yIzM"
    
    try:
        url = f"{supabase_url}/rest/v1/venues"
        data = json.dumps([venue_data]).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('apikey', supabase_key)
        req.add_header('Authorization', f'Bearer {supabase_key}')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Prefer', 'return=minimal')
        
        print(f"\nTrying to insert to: {url}")
        
        with urllib.request.urlopen(req) as response:
            print(f"Success! Status: {response.status}")
            result = response.read().decode('utf-8')
            print(f"Response: {result}")
            
    except Exception as e:
        print(f"\nError: {e}")
        if hasattr(e, 'read'):
            error_response = e.read().decode('utf-8')
            print(f"Error response: {error_response}")

def format_phone(phone: str) -> str:
    """Format phone number to E.164"""
    if not phone:
        return ""
    
    # Remove all non-digits  
    digits = ''.join(c for c in phone if c.isdigit())
    
    # Add US country code if needed
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    
    return ""

if __name__ == "__main__":
    test_single_insert()
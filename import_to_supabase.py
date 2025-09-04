#!/usr/bin/env python3
"""
Import restaurants from food_permits_restaurants.csv into Supabase
"""
import csv
import requests
import json
import uuid
import re
from datetime import datetime

def clean_phone(phone):
    """Clean and format phone number"""
    if not phone:
        return None
    
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    
    # Format as E.164 if we have 10 digits
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    else:
        return None

def clean_address(address):
    """Clean address field"""
    if not address:
        return None
    return address.strip().upper()

def import_restaurants_to_supabase():
    """Import restaurants from CSV to Supabase"""
    
    SUPABASE_URL = "https://vnnplotrwbtjtopknxgl.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZubnBsb3Ryd2J0anRvcGtueGdsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Njc4NDc1OCwiZXhwIjoyMDcyMzYwNzU4fQ.qFZl7LLGqc9CmpIfPKy8bNyHoexCB_sdre-hc08yIzM"
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    print("🚀 Starting import of restaurants to Supabase...")
    
    # First, clear existing venues
    print("🗑️  Clearing existing venues...")
    delete_url = f"{SUPABASE_URL}/rest/v1/venues"
    response = requests.delete(delete_url, headers=headers)
    print(f"Cleared existing venues: {response.status_code}")
    
    # Read and process CSV
    venues = []
    batch_size = 100
    
    with open('food_permits_restaurants.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        count = 0
        
        for row in reader:
            try:
                # Skip inactive permits
                if row.get('Active Permit', '').lower() != 'true':
                    continue
                    
                # Skip if no name
                if not row.get('Record Name', '').strip():
                    continue
                
                venue = {
                    'id': str(uuid.uuid4()),
                    'name': row.get('Record Name', '').strip().upper(),
                    'address': clean_address(row.get('Address', '')),
                    'city': row.get('City', '').strip().upper(),
                    'state': row.get('State', '').strip().upper(),
                    'postal_code': row.get('Zip', '').strip(),
                    'country': 'US',
                    'phone_e164': clean_phone(row.get('Permit Owner Business Phone', '')),
                    'website': None,
                    'latitude': float(row['Latitude']) if row.get('Latitude') and row['Latitude'].strip() else None,
                    'longitude': float(row['Longitude']) if row.get('Longitude') and row['Longitude'].strip() else None,
                    'created_at': datetime.utcnow().isoformat() + 'Z',
                    'updated_at': datetime.utcnow().isoformat() + 'Z'
                }
                
                venues.append(venue)
                count += 1
                
                # Batch insert
                if len(venues) >= batch_size:
                    insert_batch(venues, headers, SUPABASE_URL)
                    venues = []
                    print(f"Processed {count} venues...")
                    
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
    
    # Insert remaining venues
    if venues:
        insert_batch(venues, headers, SUPABASE_URL)
    
    print(f"✅ Import completed! Processed {count} total venues")

def insert_batch(venues, headers, supabase_url):
    """Insert a batch of venues"""
    url = f"{supabase_url}/rest/v1/venues"
    response = requests.post(url, headers=headers, json=venues)
    
    if response.status_code not in [201, 200]:
        print(f"❌ Error inserting batch: {response.status_code} - {response.text}")
    else:
        print(f"✅ Inserted {len(venues)} venues")

if __name__ == "__main__":
    import_restaurants_to_supabase()
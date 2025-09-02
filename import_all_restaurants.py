#!/usr/bin/env python3
"""
Import all restaurants from food_permits_restaurants.csv into DynamoDB
"""
import boto3
import csv
import json
from decimal import Decimal
from botocore.exceptions import ClientError

def clean_data_for_dynamodb(data):
    """Convert all numeric values to Decimal for DynamoDB compatibility"""
    if isinstance(data, dict):
        return {k: clean_data_for_dynamodb(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_dynamodb(item) for item in data]
    elif isinstance(data, float):
        # Check for NaN values
        if str(data) == 'nan' or data != data or data == float('inf') or data == float('-inf'):
            return None
        try:
            return Decimal(str(data))
        except:
            return None
    elif isinstance(data, int):
        return Decimal(str(data))
    elif data == '' or data is None or str(data).lower() in ['nan', 'null', 'none']:
        return None
    else:
        # Clean string data and return
        clean_str = str(data).strip()
        # Check if it's a problematic string that looks like a number
        if clean_str.lower() in ['nan', 'null', 'none', '']:
            return None
        return clean_str

def import_all_restaurants():
    """Import all restaurants from CSV to DynamoDB"""
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('restaurants')
    
    print("🚀 Starting import of all restaurants...")
    
    # Read and process CSV
    restaurants = []
    with open('food_permits_restaurants.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            try:
                # Parse coordinates with better error handling
                lat = None
                lon = None
                
                if row['Latitude'] and str(row['Latitude']).strip() not in ['', 'nan', 'NaN', 'null']:
                    try:
                        lat_float = float(row['Latitude'])
                        if lat_float != lat_float or lat_float == float('inf') or lat_float == float('-inf'):  # Check for NaN/inf
                            lat = None
                        else:
                            lat = Decimal(str(lat_float))
                    except (ValueError, TypeError):
                        lat = None
                
                if row['Longitude'] and str(row['Longitude']).strip() not in ['', 'nan', 'NaN', 'null']:
                    try:
                        lon_float = float(row['Longitude'])
                        if lon_float != lon_float or lon_float == float('inf') or lon_float == float('-inf'):  # Check for NaN/inf
                            lon = None
                        else:
                            lon = Decimal(str(lon_float))
                    except (ValueError, TypeError):
                        lon = None
                
                restaurant = {
                    'id': row['id'].strip() if row['id'] else None,
                    'record_id': row['Record ID'].strip() if row['Record ID'] else None,
                    'name': row['Record Name'].strip().upper() if row['Record Name'] else None,  # Normalize name
                    'address': row['Address'].strip() if row['Address'] else None,
                    'city': row['City'].strip() if row['City'] else None,
                    'state': row['State'].strip() if row['State'] else None,
                    'zip': row['Zip'].strip() if row['Zip'] else None,
                    'business_type': row['Business Type'].strip() if row['Business Type'] else None,
                    'permit_status': row['Permit Status'].strip() if row['Permit Status'] else None,
                    'active': row['Active Permit'].lower() == 'true' if row['Active Permit'] else False,
                    'phone': row['Permit Owner Business Phone'].strip() if row['Permit Owner Business Phone'] else None,
                    'email': row['Permit Owner Email'].strip() if row['Permit Owner Email'] else None,
                    'owner': row['Permit Owner Full Name'].strip() if row['Permit Owner Full Name'] else None,
                    'last_updated': row['Last Updated'].strip() if row['Last Updated'] else None,
                    'latitude': lat,  # Already converted to Decimal or None
                    'longitude': lon,  # Already converted to Decimal or None
                    'record_open_date': row['Record Open Date'].strip() if row['Record Open Date'] else None,
                    'record_issue_date': row['Record Issue Date'].strip() if row['Record Issue Date'] else None
                }
                
                # Remove any empty or None values to avoid DynamoDB issues
                restaurant = {k: v for k, v in restaurant.items() if v is not None and v != ''}
                restaurants.append(restaurant)
                
            except Exception as e:
                print(f"❌ Error processing row {row.get('id', 'unknown')}: {e}")
                continue
    
    print(f"📊 Processed {len(restaurants)} restaurants from CSV")
    
    # Batch write to DynamoDB
    imported_count = 0
    failed_count = 0
    
    # Process in batches of 25 (DynamoDB limit)
    batch_size = 25
    for i in range(0, len(restaurants), batch_size):
        batch = restaurants[i:i + batch_size]
        
        try:
            with table.batch_writer() as batch_writer:
                for restaurant in batch:
                    # Only import active restaurants with valid data
                    if restaurant.get('active') and restaurant.get('name'):
                        batch_writer.put_item(Item=restaurant)
                        imported_count += 1
                    else:
                        failed_count += 1
            
            if imported_count % 100 == 0:
                print(f"✅ Imported {imported_count} restaurants...")
                
        except Exception as e:
            print(f"❌ Batch import failed for batch starting at {i}: {e}")
            failed_count += len(batch)
            continue
    
    print(f"🎉 Import Complete!")
    print(f"✅ Successfully imported: {imported_count} restaurants")
    print(f"❌ Failed/skipped: {failed_count} records")
    print(f"📍 Total processed: {len(restaurants)} records")
    
    # Query a few examples to verify
    print("\n🔍 Sample restaurants in database:")
    try:
        response = table.scan(Limit=5)
        for item in response['Items']:
            print(f"  • {item['name']} - {item['city']}, {item['state']}")
    except Exception as e:
        print(f"❌ Error querying sample data: {e}")

if __name__ == "__main__":
    import_all_restaurants()
import csv

# Target zip codes (south of 52, west of 15)
target_zips = [
    '92101', '92102', '92103', '92104', '92105', '92106', '92107', '92108',
    '92109', '92110', '92111', '92113', '92116', '92117', '92123',
    '92037', '92092', '92093',  # La Jolla
    '92134', '92135', '92140', '92152', '92153', '92154'  # South Bay
]

# Business types that are likely restaurants/bars
restaurant_types = [
    'Restaurant Food Facility',
    'Caterer',
    'Caterer - Direct Sales',
    'Limited Food Prep Cart',  # Some might be bar carts
    'Single Operating Site',  # Could be restaurants
    'Miscellaneous Food Facility',  # Could include bars
]

# Keywords to identify bars/restaurants in the name
positive_keywords = [
    'restaurant', 'grill', 'bar', 'pub', 'brewery', 'brewpub', 'taproom',
    'tavern', 'lounge', 'club', 'cantina', 'bistro', 'kitchen', 'cafe',
    'steakhouse', 'sushi', 'pizza', 'taco', 'burrito', 'mexican', 'italian', 
    'thai', 'chinese', 'seafood', 'bbq', 'barbecue', 'gastropub', 'wine', 
    'cocktail', 'spirits', 'beer', 'dining', 'eatery', 'chophouse'
]

# Keywords to exclude (non-restaurant facilities)
negative_keywords = [
    'school', 'hospital', 'medical', 'care facility', 'senior', 'nursing',
    'daycare', 'child', 'market', 'grocery', '7-eleven', 'shell', 'chevron',
    'mobil', 'arco', 'vons', 'ralphs', 'albertsons', 'cvs', 'walgreens',
    'rite aid', 'target', 'walmart', 'costco', 'gas station'
]

def should_include(row):
    """Determine if a facility should be included"""
    
    # Check zip code (handle full zip codes like 92101-1234)
    zip_code = row['Zip'].split('-')[0] if row['Zip'] else ''
    if zip_code not in target_zips:
        return False
    
    # Check business type
    business_type = row['Business Type'] if row['Business Type'] else ''
    name = row['Record Name'].lower() if row['Record Name'] else ''
    
    # Check if it's a restaurant type
    is_restaurant_type = any(rtype.lower() in business_type.lower() for rtype in restaurant_types)
    
    # Check for negative keywords first
    has_negative = any(neg in name for neg in negative_keywords)
    if has_negative:
        # Only include if it has strong positive indicators
        has_strong_positive = any(pos in name for pos in ['bar', 'pub', 'brewery', 'cocktail', 'wine'])
        if not has_strong_positive:
            return False
    
    # Include if it's a restaurant type
    if is_restaurant_type:
        return True
    
    # For other types, check if name suggests it's a restaurant/bar
    has_positive = any(pos in name for pos in positive_keywords)
    if has_positive:
        return True
    
    return False

# Read and filter the food facility permits
filtered_facilities = []

with open('Food_Facility_Permits.csv', 'r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Only include active permits
        if row.get('Active Permit', '').lower() == 'true':
            if should_include(row):
                filtered_facilities.append(row)

# Sort by zip code, then by facility name
filtered_facilities.sort(key=lambda x: (x['Zip'], x['Record Name']))

# Write to output CSV
if filtered_facilities:
    with open('food_permits_restaurants.csv', 'w', newline='', encoding='utf-8') as file:
        fieldnames = filtered_facilities[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_facilities)

print(f"Filtered to {len(filtered_facilities)} restaurant/bar food permits")
print(f"\nFacilities by zip code:")

# Count by zip
zip_counts = {}
for facility in filtered_facilities:
    zip_code = facility['Zip'].split('-')[0] if facility['Zip'] else 'Unknown'
    zip_counts[zip_code] = zip_counts.get(zip_code, 0) + 1

for zip_code in sorted(zip_counts.keys()):
    print(f"  {zip_code}: {zip_counts[zip_code]} facilities")

print(f"\nFirst 15 facilities:")
for i, facility in enumerate(filtered_facilities[:15], 1):
    print(f"{i}. {facility['Record Name']} - {facility['Address']} ({facility['Zip']}) - {facility['Business Type']}")
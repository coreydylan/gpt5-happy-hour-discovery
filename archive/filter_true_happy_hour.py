import csv

# Target zip codes (south of 52, west of 15)
target_zips = [
    '92101', '92102', '92103', '92104', '92105', '92106', '92107', '92108',
    '92109', '92110', '92111', '92113', '92116', '92117', '92123',
    '92037', '92092', '92093',  # La Jolla
    '92134', '92135', '92140', '92152', '92153', '92154'  # South Bay
]

# Activity descriptions that likely have happy hours
keep_activities = [
    'full-service restaurant',
    'limited-service restaurant',
    'limited-service eating',
    'drinking place',
    'food services & drinking',
    'snack & nonalcoholic beverage bar',  # Some serve alcohol
    'caterer',  # Some do events with bars
    'beer, wine',
    'brewery',
    'winery',
    'cafeteria',  # Some corporate ones have bars
]

# Activity descriptions to definitely exclude
exclude_activities = [
    'plumbing',
    'heating',
    'barber',
    'beauty',
    'hair',
    'cottage food',
    'mobile food',
    'public relation',
    'accountant',
    'legal service',
    'book publisher',
    'publishing',
    'wholesale',
    'grocery store',
    'food mfg',
    'personal service',
    'office',
    'contractor',
    'equipment',
    'supplies',
    'market',  # Usually convenience stores
    'liquor store',  # Retail, not consumption
]

# Keywords in names that suggest true restaurants/bars
positive_name_keywords = [
    'restaurant', 'grill', 'bar', 'pub', 'brewery', 'brewpub', 'taproom',
    'tavern', 'lounge', 'club', 'cantina', 'bistro', 'kitchen', 'cafe',
    'steakhouse', 'sushi', 'pizza', 'mexican', 'italian', 'thai', 'chinese',
    'seafood', 'bbq', 'barbecue', 'gastropub', 'wine', 'cocktail', 'spirits'
]

# Keywords in names that suggest NOT happy hour venues
negative_name_keywords = [
    'market', 'mart', 'liquor', 'grocery', 'convenience', 'gas', 
    'plumbing', 'heating', 'air', 'barber', 'salon', 'hair', 'nail',
    'law', 'legal', 'accounting', 'cpa', 'tax', 'mobile', 'truck'
]

def should_include(row):
    """Determine if a business should be included in the happy hour list"""
    
    # Check zip code
    zip_code = row['ZIP'].split('-')[0] if row['ZIP'] else ''
    if zip_code not in target_zips:
        return False
    
    # Get lowercase versions for comparison
    activity = row['ACTIVITY DESC'].lower() if row['ACTIVITY DESC'] else ''
    name = row['DBA NAME'].lower() if row['DBA NAME'] else ''
    
    # First check exclusions
    for exclude in exclude_activities:
        if exclude in activity:
            # Check if there's a strong positive override in the name
            has_positive = any(pos in name for pos in positive_name_keywords)
            if not has_positive:
                return False
    
    for exclude in negative_name_keywords:
        if exclude in name:
            # Check if there's a strong positive indicator in activity
            has_positive = any(keep in activity for keep in keep_activities)
            if not has_positive:
                return False
    
    # Check inclusions
    for keep in keep_activities:
        if keep in activity:
            return True
    
    # Check positive name keywords
    for keyword in positive_name_keywords:
        if keyword in name:
            return True
    
    return False

# Read and filter the happy hour candidates
filtered_businesses = []

with open('happy_hour_candidates.csv', 'r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        if should_include(row):
            filtered_businesses.append(row)

# Sort by zip code, then by business name
filtered_businesses.sort(key=lambda x: (x['ZIP'], x['DBA NAME']))

# Write to output CSV
if filtered_businesses:
    with open('true_happy_hour_venues.csv', 'w', newline='', encoding='utf-8') as file:
        fieldnames = filtered_businesses[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_businesses)

print(f"Filtered down to {len(filtered_businesses)} likely happy hour venues")
print(f"\nVenues by zip code:")

# Count by zip
zip_counts = {}
for business in filtered_businesses:
    zip_code = business['ZIP'].split('-')[0] if business['ZIP'] else 'Unknown'
    zip_counts[zip_code] = zip_counts.get(zip_code, 0) + 1

for zip_code in sorted(zip_counts.keys()):
    print(f"  {zip_code}: {zip_counts[zip_code]} venues")

print(f"\nFirst 15 venues:")
for i, business in enumerate(filtered_businesses[:15], 1):
    print(f"{i}. {business['DBA NAME']} - {business['ADDRESS']} ({business['ZIP']}) - {business['ACTIVITY DESC']}")
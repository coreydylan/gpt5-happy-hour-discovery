import csv

# Keywords to identify restaurants and bars
restaurant_keywords = [
    'restaurant', 'dining', 'eating', 'food', 'drink', 'bar', 'tavern', 
    'pub', 'brewpub', 'brewery', 'grill', 'cafe', 'bistro', 'kitchen',
    'cocktail', 'lounge', 'club', 'wine', 'taproom', 'gastropub',
    'cantina', 'pizzeria', 'steakhouse', 'sushi', 'barbecue', 'bbq'
]

# NAICS codes for restaurants and drinking establishments
restaurant_naics = [
    '722211',  # Limited-Service Restaurants
    '7222',    # Limited-Service Eating Places
    '72241',   # Drinking Places (Alcoholic Beverages)
    '722511',  # Full-Service Restaurants
    '722513',  # Limited-Service Restaurants
    '722514',  # Cafeterias, Grill Buffets, and Buffets
    '722515',  # Snack and Nonalcoholic Beverage Bars
]

def is_restaurant(row):
    """Check if a business is likely a restaurant/bar"""
    dba_name = row['DBA NAME'].lower() if row['DBA NAME'] else ''
    activity = row['ACTIVITY DESC'].lower() if row['ACTIVITY DESC'] else ''
    naics = str(row['NAICS']) if row['NAICS'] else ''
    
    # Check NAICS code
    if naics in restaurant_naics:
        return True
    
    # Check keywords in name or activity
    for keyword in restaurant_keywords:
        if keyword in dba_name or keyword in activity:
            return True
    
    return False

# Read and filter both CSV files
filtered_businesses = []
seen_accts = set()

for filename in ['tr_active1.csv', 'tr_active2.csv']:
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Skip duplicates
            acct_num = row['BUSINESS ACCT#']
            if acct_num in seen_accts:
                continue
            
            if is_restaurant(row):
                filtered_businesses.append(row)
                seen_accts.add(acct_num)

# Sort by business name
filtered_businesses.sort(key=lambda x: x['DBA NAME'])

# Write to output CSV
if filtered_businesses:
    with open('happy_hour_candidates.csv', 'w', newline='', encoding='utf-8') as file:
        fieldnames = filtered_businesses[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_businesses)

print(f"Found {len(filtered_businesses)} potential happy hour locations")
print("\nFirst 20 results:")
for i, business in enumerate(filtered_businesses[:20], 1):
    print(f"{i}. {business['DBA NAME']} - {business['ADDRESS']} - {business['ACTIVITY DESC']}")
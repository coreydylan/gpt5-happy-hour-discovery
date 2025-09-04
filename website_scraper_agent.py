"""
Website Scraper Agent - Specialized Lambda function for scraping restaurant websites
Focuses specifically on finding happy hour information from official restaurant sites
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Optional
import time

def lambda_handler(event, context):
    """
    Website scraper agent for happy hour information
    """
    try:
        # Parse input
        restaurant_name = event.get('restaurant_name', '')
        restaurant_address = event.get('restaurant_address', '')
        job_id = event.get('job_id', '')
        
        print(f"Website scraper starting for: {restaurant_name}")
        
        # Find restaurant website
        website_url = find_restaurant_website(restaurant_name, restaurant_address)
        
        if not website_url:
            return {
                'agent': 'site_agent',
                'job_id': job_id,
                'status': 'completed',
                'data': {
                    'found': False,
                    'reason': 'Could not find restaurant website',
                    'confidence': 0.0
                }
            }
        
        print(f"Found website: {website_url}")
        
        # Scrape happy hour information
        happy_hour_data = scrape_happy_hour_info(website_url, restaurant_name)
        
        return {
            'agent': 'site_agent',
            'job_id': job_id,
            'status': 'completed',
            'data': happy_hour_data
        }
        
    except Exception as e:
        print(f"Website scraper error: {e}")
        return {
            'agent': 'site_agent',
            'job_id': job_id,
            'status': 'failed',
            'error': str(e)
        }

def find_restaurant_website(restaurant_name: str, restaurant_address: str) -> Optional[str]:
    """
    Find the official website for a restaurant using search patterns
    """
    
    # Common website patterns
    name_clean = re.sub(r'[^a-zA-Z0-9]', '', restaurant_name.lower())
    
    possible_urls = [
        f"https://{name_clean}.com",
        f"https://{name_clean}restaurant.com",
        f"https://www.{name_clean}.com",
        f"https://www.{name_clean}restaurant.com",
    ]
    
    # Try common patterns first
    for url in possible_urls:
        if test_website_exists(url):
            return url
    
    # If name has multiple words, try combinations
    words = restaurant_name.lower().split()
    if len(words) > 1:
        combined = ''.join(words)
        for ext in ['.com', 'restaurant.com']:
            url = f"https://{combined}{ext}"
            if test_website_exists(url):
                return url
            url = f"https://www.{combined}{ext}"
            if test_website_exists(url):
                return url
    
    return None

def test_website_exists(url: str) -> bool:
    """Test if a website exists and is accessible"""
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

def scrape_happy_hour_info(website_url: str, restaurant_name: str) -> Dict[str, Any]:
    """
    Scrape happy hour information from restaurant website
    """
    try:
        # Get main page
        response = requests.get(website_url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find happy hour related links/pages
        happy_hour_links = find_happy_hour_pages(soup, website_url)
        
        all_happy_hour_data = []
        
        # Scrape main page
        main_page_data = extract_happy_hour_from_page(soup, website_url)
        if main_page_data:
            all_happy_hour_data.append(main_page_data)
        
        # Scrape dedicated happy hour pages
        for link in happy_hour_links:
            try:
                page_response = requests.get(link, timeout=10)
                page_soup = BeautifulSoup(page_response.content, 'html.parser')
                page_data = extract_happy_hour_from_page(page_soup, link)
                if page_data:
                    all_happy_hour_data.append(page_data)
            except Exception as e:
                print(f"Error scraping {link}: {e}")
        
        # Aggregate findings
        if all_happy_hour_data:
            return {
                'found': True,
                'website_url': website_url,
                'happy_hour_data': all_happy_hour_data,
                'confidence': calculate_confidence(all_happy_hour_data),
                'sources': [website_url] + happy_hour_links
            }
        else:
            return {
                'found': False,
                'website_url': website_url,
                'reason': 'No happy hour information found on website',
                'confidence': 0.0
            }
            
    except Exception as e:
        print(f"Error scraping {website_url}: {e}")
        return {
            'found': False,
            'website_url': website_url,
            'error': str(e),
            'confidence': 0.0
        }

def find_happy_hour_pages(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Find links to happy hour or specials pages"""
    
    happy_hour_keywords = [
        'happy hour', 'happyhour', 'happy-hour',
        'specials', 'promotions', 'deals',
        'menu', 'drink menu', 'bar menu'
    ]
    
    links = []
    
    # Find all links
    for a_tag in soup.find_all('a', href=True):
        href = a_tag.get('href')
        text = a_tag.get_text().lower()
        
        # Check if link text contains happy hour keywords
        for keyword in happy_hour_keywords:
            if keyword in text or keyword in href.lower():
                full_url = urljoin(base_url, href)
                if full_url not in links:
                    links.append(full_url)
                break
    
    return links

def extract_happy_hour_from_page(soup: BeautifulSoup, page_url: str) -> Optional[Dict[str, Any]]:
    """
    Extract happy hour information from a webpage
    """
    
    # Look for happy hour text patterns
    text = soup.get_text().lower()
    
    happy_hour_patterns = [
        r'happy hour.*?(\w+day).*?(\d{1,2}(?::\d{2})?\s*[ap]m)\s*-\s*(\d{1,2}(?::\d{2})?\s*[ap]m)',
        r'(\w+day).*?(\d{1,2}(?::\d{2})?\s*[ap]m)\s*-\s*(\d{1,2}(?::\d{2})?\s*[ap]m).*?happy hour',
        r'(\w+day)\s+to\s+(\w+day).*?(\d{1,2}(?::\d{2})?\s*[ap]m)\s*-\s*(\d{1,2}(?::\d{2})?\s*[ap]m)'
    ]
    
    schedule = {}
    offers = []
    
    # Extract schedule
    for pattern in happy_hour_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            groups = match.groups()
            if len(groups) >= 3:
                day = groups[0].lower()
                start_time = groups[1]
                end_time = groups[2]
                
                if 'monday' in day or 'tuesday' in day or 'wednesday' in day or 'thursday' in day or 'friday' in day:
                    schedule[day] = [{'start': start_time, 'end': end_time}]
    
    # Look for drink specials and prices
    price_patterns = [
        r'\$(\d+(?:\.\d{2})?)',
        r'(\w+.*?)\s+\$(\d+(?:\.\d{2})?)'
    ]
    
    # Find menu items and prices
    for element in soup.find_all(['div', 'li', 'tr'], class_=re.compile('menu|item|price', re.I)):
        element_text = element.get_text()
        if '$' in element_text:
            # Extract drink/food items with prices
            lines = element_text.strip().split('\n')
            for line in lines:
                if '$' in line and any(word in line.lower() for word in ['beer', 'wine', 'cocktail', 'drink', 'margarita', 'sangria']):
                    offers.append({
                        'type': 'drink',
                        'description': line.strip()
                    })
    
    if schedule or offers:
        return {
            'schedule': schedule,
            'offers': offers,
            'source_url': page_url,
            'raw_text': text[:500]  # First 500 chars for debugging
        }
    
    return None

def calculate_confidence(data_list: List[Dict]) -> float:
    """Calculate confidence score based on data quality"""
    
    if not data_list:
        return 0.0
    
    score = 0.0
    
    for data in data_list:
        # Points for having schedule
        if data.get('schedule'):
            score += 0.4
        
        # Points for having offers
        if data.get('offers'):
            score += 0.3
        
        # Points for having source URL
        if data.get('source_url'):
            score += 0.2
        
        # Points for having detailed text
        if data.get('raw_text') and len(data.get('raw_text', '')) > 100:
            score += 0.1
    
    return min(score, 1.0)
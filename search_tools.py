"""
Web search tools for finding restaurant happy hour information
"""
import httpx
import asyncio
from typing import Dict, Any, Optional
import os
from bs4 import BeautifulSoup
import json

class RestaurantSearchTools:
    """Tools for searching restaurant happy hour information"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_google(self, query: str) -> Dict[str, Any]:
        """
        Search Google for restaurant information
        Note: In production, you'd use Google Custom Search API
        """
        try:
            # For demo, we'll use a simple web scraping approach
            # In production, use Google Custom Search API with API key
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            response = await self.client.get(search_url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Extract search results - simplified for demo
                results = []
                for g in soup.find_all('div', class_='g')[:3]:  # Get top 3 results
                    title = g.find('h3')
                    snippet = g.find('span', class_='st')
                    if title:
                        results.append({
                            'title': title.text,
                            'snippet': snippet.text if snippet else ''
                        })
                
                return {
                    'status': 'success',
                    'results': results,
                    'source': 'google_search'
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Search failed with status {response.status_code}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def search_yelp(self, restaurant_name: str, location: str) -> Dict[str, Any]:
        """
        Search Yelp for restaurant information
        Note: Requires Yelp API key for production use
        """
        try:
            # Yelp Fusion API endpoint
            yelp_api_key = os.getenv('YELP_API_KEY')
            
            if not yelp_api_key:
                # Return mock data for demo if no API key
                return {
                    'status': 'limited',
                    'message': 'Yelp API key not configured',
                    'tip': 'Many Yelp reviews mention happy hour times and specials'
                }
            
            headers = {
                'Authorization': f'Bearer {yelp_api_key}'
            }
            
            # Search for the business
            search_url = 'https://api.yelp.com/v3/businesses/search'
            params = {
                'term': restaurant_name,
                'location': location,
                'limit': 1
            }
            
            response = await self.client.get(search_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['businesses']:
                    business = data['businesses'][0]
                    
                    # Get detailed info
                    detail_url = f"https://api.yelp.com/v3/businesses/{business['id']}"
                    detail_response = await self.client.get(detail_url, headers=headers)
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        
                        return {
                            'status': 'success',
                            'business_name': detail_data.get('name'),
                            'phone': detail_data.get('phone'),
                            'hours': detail_data.get('hours', []),
                            'categories': detail_data.get('categories', []),
                            'rating': detail_data.get('rating'),
                            'review_count': detail_data.get('review_count'),
                            'url': detail_data.get('url'),
                            'source': 'yelp_api'
                        }
            
            return {
                'status': 'not_found',
                'message': 'Restaurant not found on Yelp'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def search_restaurant_website(self, restaurant_name: str, address: str) -> Dict[str, Any]:
        """
        Try to find and scrape the restaurant's official website
        """
        try:
            # First, search for the restaurant website
            query = f"{restaurant_name} {address} official website menu happy hour"
            google_results = await self.search_google(query)
            
            if google_results['status'] == 'success' and google_results['results']:
                # Look for happy hour mentions in search results
                happy_hour_mentions = []
                for result in google_results['results']:
                    snippet = result.get('snippet', '').lower()
                    if any(term in snippet for term in ['happy hour', 'happy hr', 'aloha hour', 'special pricing']):
                        happy_hour_mentions.append({
                            'source': result.get('title'),
                            'mention': result.get('snippet')
                        })
                
                return {
                    'status': 'success',
                    'happy_hour_mentions': happy_hour_mentions,
                    'source': 'web_search'
                }
            
            return {
                'status': 'limited',
                'message': 'Could not find website information'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool call based on the function name and arguments
    """
    tools = RestaurantSearchTools()
    
    try:
        if tool_name == "search_google":
            result = await tools.search_google(arguments.get('query', ''))
        elif tool_name == "search_yelp":
            result = await tools.search_yelp(
                arguments.get('restaurant_name', ''),
                arguments.get('address', '')
            )
        elif tool_name == "search_restaurant_website":
            result = await tools.search_restaurant_website(
                arguments.get('restaurant_name', ''),
                arguments.get('location', '')
            )
        else:
            result = {
                'status': 'error',
                'message': f'Unknown tool: {tool_name}'
            }
    finally:
        await tools.close()
    
    return result
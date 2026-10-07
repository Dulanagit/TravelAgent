import os
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from typing import List, Dict, Any
import datetime

# Helper function for extracting text from a webpage
def read_website_content(url: str) -> str:
    """Uses requests and BeautifulSoup to extract text from a given URL."""
    try:
        # User-Agent header is important for scraping
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        # Limit text length to avoid context window explosion in LLMs
        return text[:5000]
    except Exception as e:
        print(f"Error reading {url}: {e}")
        return ""

def get_sri_lanka_weather(city: str) -> Dict[str, Any]:
    """Uses Open-Meteo to fetch real-time weather and forecast."""
    # First, geocode the city (assuming it's in Sri Lanka)
    geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    try:
        geo_response = requests.get(geocode_url).json()
        if not geo_response.get("results"):
            # Default to Colombo if not found
            lat, lon = 6.9271, 79.8612
        else:
            lat = geo_response["results"][0]["latitude"]
            lon = geo_response["results"][0]["longitude"]
            
        # Get current weather
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_response = requests.get(weather_url).json()
        
        current_weather = weather_response.get("current_weather", {})
        return {
            "temperature": current_weather.get("temperature"),
            "weathercode": current_weather.get("weathercode"),
            # Weathercode mapping (simplified)
            "is_raining": current_weather.get("weathercode", 0) in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99],
            "city": city
        }
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return {"temperature": 30.0, "is_raining": False, "city": city}

def get_current_news(topic: str) -> str:
    """Uses DuckDuckGo News Search for Sri Lanka."""
    try:
        ddgs = DDGS()
        # Search for news
        results = ddgs.text(f"{topic} Sri Lanka", max_results=3)
        news_summary = ""
        for r in results:
            news_summary += f"- {r['title']}: {r['body']}\n"
        return news_summary
    except Exception as e:
        print(f"Error fetching news: {e}")
        return "No recent news found."

from dotenv import load_dotenv
load_dotenv()

def search_hotels(city: str, start_date: str, end_date: str, budget: float) -> List[Dict[str, Any]]:
    """
    Search hotels using RapidAPI Booking.com scraper (booking-com15).
    Requires RAPIDAPI_KEY environment variable.
    """
    api_key = os.environ.get("RAPIDAPI_KEY")
    
    mock_fallback = [
        {"name": f"Mock Hotel {city} 1", "price_per_night": budget * 0.1, "rating": 4.5},
        {"name": f"Mock Hotel {city} 2", "price_per_night": budget * 0.15, "rating": 4.8},
        {"name": f"Mock Hotel {city} 3", "price_per_night": budget * 0.05, "rating": 3.9},
    ]

    if not api_key:
        print("Warning: RAPIDAPI_KEY not found in .env. Returning mock data.")
        return mock_fallback
        
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "booking-com15.p.rapidapi.com"
    }
    
    try:
        # Step 1: Get destination ID
        print(f"Fetching destination ID for {city}...")
        dest_url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
        dest_response = requests.get(dest_url, headers=headers, params={"query": city}, timeout=10)
        dest_response.raise_for_status()
        dest_data = dest_response.json()
        
        dest_id = None
        if dest_data and "data" in dest_data and len(dest_data["data"]) > 0:
            dest_id = dest_data["data"][0].get("dest_id")
            
        if not dest_id:
            print(f"Could not find destination ID for {city}. Returning mock data.")
            return mock_fallback

        # Step 2: Search hotels
        print(f"Searching real hotels for {city} via RapidAPI (dest_id: {dest_id})...")
        search_url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
        params = {
            "dest_id": dest_id,
            "search_type": "CITY",
            "arrival_date": start_date,
            "departure_date": end_date,
            "adults": "1",
            "room_qty": "1",
            "page_number": "1",
            "units": "metric",
            "temperature_unit": "c",
            "languagecode": "en-us",
            "currency_code": "USD"
        }
        
        search_response = requests.get(search_url, headers=headers, params=params, timeout=15)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        hotels = []
        if "data" in search_data and "hotels" in search_data["data"]:
            for item in search_data["data"]["hotels"][:5]:  # Get top 5
                prop = item.get("property", {})
                price_breakdown = prop.get("priceBreakdown", {})
                gross_price = price_breakdown.get("grossPrice", {})
                price = gross_price.get("value", 0)
                
                # Approximate price per night
                try:
                    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    nights = (end_dt - start_dt).days or 1
                    price_per_night = float(price) / nights
                except Exception:
                    price_per_night = float(price) if price else 0
                    
                rating = prop.get("reviewScore", 0)
                
                hotels.append({
                    "name": prop.get("name", "Unknown Hotel"),
                    "price_per_night": price_per_night,
                    "rating": float(rating) if rating else 0
                })
        
        if not hotels:
            print("No hotels found in the API response. Returning mock data.")
            return mock_fallback
            
        return hotels
        
    except Exception as e:
        print(f"Error fetching hotels from RapidAPI: {e}")
        return mock_fallback

def get_places_to_visit(city: str, preferences: str) -> List[Dict[str, Any]]:
    """Uses DuckDuckGo search to find trending spots and reads the website content."""
    try:
        ddgs = DDGS()
        # Search TripAdvisor or Reddit for activities
        search_query = f"site:tripadvisor.com OR site:reddit.com/r/srilanka best things to do in {city} {preferences}"
        results = ddgs.text(search_query, max_results=2)
        
        activities_text = ""
        for r in results:
            url = r['href']
            print(f"Reading {url} for activities...")
            content = read_website_content(url)
            activities_text += content[:1000] # Append snippet
            
        # In a full LangChain setup, an LLM would parse `activities_text` into structured JSON.
        # Here we mock the extraction based on the search success.
        if activities_text:
            return [
                {"name": f"Visit local sights in {city}", "type": "Sightseeing", "estimated_cost": 20},
                {"name": f"Try local food in {city}", "type": "Culinary", "estimated_cost": 15}
            ]
        else:
            return [{"name": f"Walk around {city}", "type": "Leisure", "estimated_cost": 0}]
    except Exception as e:
        print(f"Error fetching places: {e}")
        return []

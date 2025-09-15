#!/usr/bin/env python3
"""
Taxi Availability Application
Finds and displays the top areas in Singapore with the highest concentration of available taxis.

Enhanced with:
- Geocoding caching for faster repeated runs
- Command-line arguments for customization
- Progress indication during processing
- Retry logic for robust geocoding
- Percentage statistics for better context
"""

import argparse
import json
import os
import requests
import sys
import time
from collections import Counter
from geopy.geocoders import Nominatim
from typing import List, Tuple, Dict, Optional


def fetch_taxi_data() -> Tuple[List[Tuple[float, float]], int]:
    """
    Fetch real-time taxi data from Singapore Data.gov.sg API.
    
    Returns:
        Tuple containing:
        - List of (latitude, longitude) coordinate pairs
        - Total number of available taxis
    
    Raises:
        requests.RequestException: If API request fails
        ValueError: If response data is invalid
    """
    url = "https://api.data.gov.sg/v1/transport/taxi-availability"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract features from GeoJSON
        features = data.get('features', [])
        if not features:
            raise ValueError("No taxi data available in API response")
        
        feature = features[0]
        
        # Extract total taxi count
        total_count = feature.get('properties', {}).get('taxi_count', 0)
        
        # Extract coordinates (API returns [longitude, latitude] pairs)
        coordinates_raw = feature.get('geometry', {}).get('coordinates', [])
        
        # Convert from [longitude, latitude] to [latitude, longitude] for consistency
        coordinates = [(lat_lon[1], lat_lon[0]) for lat_lon in coordinates_raw]
        
        print(f"Successfully fetched data for {len(coordinates)} taxi locations")
        return coordinates, total_count
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Failed to fetch taxi data: {e}")
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid API response format: {e}")


def group_taxis_into_areas(coordinates: List[Tuple[float, float]], precision: int = 2) -> Dict[Tuple[float, float], int]:
    """
    Group taxi coordinates into geographical areas by rounding coordinates.
    
    Args:
        coordinates: List of (latitude, longitude) pairs
        precision: Decimal precision for coordinate rounding
    
    Returns:
        Dictionary mapping (rounded_lat, rounded_lon) to taxi count
    """
    area_counts = Counter()
    
    for lat, lon in coordinates:
        # Round to specified decimal places to create grid areas
        rounded_lat = round(lat, precision)
        rounded_lon = round(lon, precision)
        area_counts[(rounded_lat, rounded_lon)] += 1
    
    return dict(area_counts)


def get_location_name(lat: float, lon: float, refresh_cache: bool = False) -> str:
    """
    Get human-readable location name for given coordinates using reverse geocoding with caching.
    
    Args:
        lat: Latitude
        lon: Longitude
        refresh_cache: If True, bypass cache and force new lookup
    
    Returns:
        Location name string, or coordinates if geocoding fails
    """
    # Load cache if available
    cache_file = "geocoding_cache.json"
    cache = {}
    
    if os.path.exists(cache_file) and not refresh_cache:
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            print("Warning: Cache file corrupted, starting with empty cache")
            cache = {}
    
    # Create cache key
    cache_key = f"{lat:.2f},{lon:.2f}"
    
    # Check cache first
    if cache_key in cache and not refresh_cache:
        return cache[cache_key]
    
    # Implement retry logic with exponential backoff
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Initialize Nominatim geocoder
            geolocator = Nominatim(user_agent="taxi_finder_singapore")
            
            # Perform reverse geocoding
            location = geolocator.reverse(f"{lat}, {lon}", timeout=10)
            
            if location and location.address:
                result = location.address
            else:
                result = f"Area near {lat}, {lon}"
                
            # Save to cache
            cache[cache_key] = result
            with open(cache_file, 'w') as f:
                json.dump(cache, f)
                
            return result
                
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"Geocoding failed, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Geocoding failed after {max_retries} attempts: {e}")
                return f"Area near {lat}, {lon}"


def get_top_areas(area_counts: Dict[Tuple[float, float], int], limit: int = 10) -> List[Tuple[Tuple[float, float], int]]:
    """
    Get top N areas with highest taxi counts.
    
    Args:
        area_counts: Dictionary mapping coordinates to taxi counts
        limit: Number of top areas to return
    
    Returns:
        List of ((lat, lon), count) tuples sorted by count (descending)
    """
    return sorted(area_counts.items(), key=lambda x: x[1], reverse=True)[:limit]


def display_results(total_count: int, top_areas: List[Tuple[Tuple[float, float], int]], refresh_cache: bool = False) -> None:
    """
    Format and display the results.
    
    Args:
        total_count: Total number of available taxis
        top_areas: List of ((lat, lon), count) tuples for top areas
        refresh_cache: Whether to refresh the geocoding cache
    """
    print(f"Total available taxis: {total_count}")
    print(f"Top {len(top_areas)} areas with the most taxis:")
    
    print("Fetching location names...")
    for i, ((lat, lon), count) in enumerate(top_areas, 1):
        # Show progress
        print(f"Processing area {i}/{len(top_areas)}...", end="\r")
        sys.stdout.flush()
        
        print(f"{i}. Lat: {lat:.2f}, Lon: {lon:.2f} - {count} taxis")
        
        # Get location name with caching
        location_name = get_location_name(lat, lon, refresh_cache)
        print(f"   Location: {location_name}")
        
        # Generate Google Maps link
        maps_link = f"https://www.google.com/maps/search/?api=1&query={lat:.2f},{lon:.2f}"
        print(f"   Google Maps: {maps_link}")
        
        # Rate limiting for geocoding API (1 second between requests)
        if i < len(top_areas):  # Don't sleep after the last request
            time.sleep(1)
    
    # Clear the progress line
    print(" " * 50, end="\r")
    
    # Show statistics
    total_in_top_areas = sum(count for _, count in top_areas)
    percentage = (total_in_top_areas / total_count) * 100 if total_count else 0
    
    print(f"\nStatistics:")
    print(f"- The top {len(top_areas)} areas contain {total_in_top_areas} taxis")
    print(f"- This represents {percentage:.1f}% of all available taxis in Singapore")
    print(f"- Average taxis per hotspot area: {total_in_top_areas / len(top_areas):.1f}")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Find areas with highest taxi concentration in Singapore",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--top', type=int, default=10, 
                        help='Number of top areas to display')
    parser.add_argument('--precision', type=int, default=2,
                        help='Decimal precision for coordinate rounding (2=~1.1km areas)')
    parser.add_argument('--refresh-cache', action='store_true',
                        help='Force refresh of geocoding cache')
    parser.add_argument('--stats-only', action='store_true',
                        help='Show only summary statistics without location details')
    return parser.parse_args()


def main():
    """
    Main application flow.
    """
    try:
        # Parse command-line arguments
        args = parse_args()
        
        print("Fetching taxi availability data from Singapore API...")
        
        # Step 1: Fetch taxi data
        coordinates, total_count = fetch_taxi_data()
        
        if not coordinates:
            print("No taxi data available.")
            return
        
        print(f"Processing {len(coordinates)} taxi locations...")
        
        # Step 2: Group taxis into areas with specified precision
        area_counts = group_taxis_into_areas(coordinates, args.precision)
        
        print(f"Found {len(area_counts)} distinct areas")
        
        # Step 3: Get top N areas
        top_areas = get_top_areas(area_counts, limit=args.top)
        
        # Step 4: Display results
        print("\n" + "="*60)
        
        if args.stats_only:
            # Display only statistics
            total_in_top_areas = sum(count for _, count in top_areas)
            percentage = (total_in_top_areas / total_count) * 100 if total_count else 0
            
            print(f"Total available taxis: {total_count}")
            print(f"Top {len(top_areas)} areas contain {total_in_top_areas} taxis ({percentage:.1f}%)")
            print(f"Average taxis per hotspot area: {total_in_top_areas / len(top_areas):.1f}")
        else:
            # Display full results with location details
            display_results(total_count, top_areas, args.refresh_cache)
        
    except requests.RequestException as e:
        print(f"Network error: {e}")
        print("Please check your internet connection and try again.")
    except ValueError as e:
        print(f"Data error: {e}")
        print("The API response format may have changed.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Please try again or contact support.")


if __name__ == "__main__":
    main()
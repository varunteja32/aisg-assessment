# Taxi Availability Application

This Python application finds and displays the top areas in Singapore with the highest concentration of available taxis using real-time data from the Singapore government API.

## Features

- Fetches real-time taxi location data from Data.gov.sg API
- Groups taxis into geographical areas using coordinate rounding
- Identifies areas with highest taxi concentration
- Provides human-readable location names using reverse geocoding
- Generates Google Maps links for each location
- Caches geocoding results for faster repeated runs
- Displays insightful statistics about taxi distribution
- Handles API errors and network issues gracefully

## Requirements

- Python 3.7+
- Internet connection for API access and geocoding

## Installation

1. Navigate to the Assignment 2 directory:

   ```bash
   cd "Assignment 2"
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the application with default settings:

```bash
python taxi_finder.py
```

### Command-line Options

Customize the application behavior:

```bash
# Show top 15 areas instead of 10
python taxi_finder.py --top 15

# Use higher precision (smaller areas)
python taxi_finder.py --precision 3

# Force fresh geocoding lookups
python taxi_finder.py --refresh-cache

# Show only summary statistics
python taxi_finder.py --stats-only
```

## Sample Output

```
Total available taxis: 2182
Top 10 areas with the most taxis:
1. Lat: 1.36, Lon: 103.99 - 75 taxis
   Location: Jewel Changi Airport, 78, T1 Boulevard, Singapur East, Changi, Southeast, Singapore, 819666, Singapore
   Google Maps: https://www.google.com/maps/search/?api=1&query=1.36,103.99
2. Lat: 1.28, Lon: 103.85 - 44 taxis
   Location: The Ogilvy Centre, 35, Robinson Road, Golden Shoe, Downtown Core, Central, Singapore, 068876, Singapore
   Google Maps: https://www.google.com/maps/search/?api=1&query=1.28,103.85

Statistics:
- The top 10 areas contain 359 taxis
- This represents 16.5% of all available taxis in Singapore
- Average taxis per hotspot area: 35.9
```

## How It Works

### Area Grouping Algorithm

The application uses a grid-based approach to group taxis:

- Coordinates are rounded to 2 decimal places by default
- This creates approximately 1.1km × 1.1km grid cells
- Taxis within the same grid cell are counted together
- Precision is adjustable via command-line options

### Geocoding Cache

- Location names are stored in a local JSON file (`geocoding_cache.json`)
- Repeated lookups use the cached data, dramatically reducing runtime
- Cache can be refreshed with the `--refresh-cache` option

### Data Processing Flow

1. **API Data Fetching**: Retrieves GeoJSON data from `https://api.data.gov.sg/v1/transport/taxi-availability`
2. **Coordinate Conversion**: Converts API format [longitude, latitude] to [latitude, longitude]
3. **Area Grouping**: Groups taxis by rounded coordinates
4. **Ranking**: Sorts areas by taxi count in descending order
5. **Geocoding**: Converts coordinates to human-readable addresses with caching
6. **Output Formatting**: Displays results with location names, map links, and statistics

### Error Handling & Robustness

- Implements retry logic with exponential backoff for geocoding failures
- Handles network connectivity issues gracefully
- Provides informative error messages for different failure scenarios
- Continues processing even if individual geocoding requests fail

## Dependencies

- `requests`: HTTP API calls to Singapore government API
- `geopy`: Reverse geocoding using Nominatim service

## Technical Details

- **Grid Resolution**: Configurable, default 2 decimal places (~1.1km grid cells in Singapore)
- **API Endpoint**: Data.gov.sg taxi availability service
- **Geocoding Service**: OpenStreetMap Nominatim
- **Coordinate System**: WGS84 (latitude, longitude)
- **Rate Limiting**: 1 request per second for geocoding
- **Caching**: Local JSON file storage for geocoding results

## Notes

- The application fetches real-time data, so results will vary based on current taxi distribution
- Geocoding requests are rate-limited to comply with service usage policies
- The grid-based grouping provides a good balance between granularity and meaningful area representation
- First run may take longer due to geocoding lookups, subsequent runs are much faster

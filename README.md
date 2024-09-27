# GitHub User Geolocation

This Python script processes a list of GitHub contributors and attempts to geolocate them based on their GitHub profiles or other available information. The script generates a GeoJSON file containing the geographical locations of the contributors.

## Features

- Reads a list of contributors from a text file
- Searches for GitHub users by name or email
- Retrieves user location information from GitHub profiles
- Geocodes location strings using multiple services (Nominatim, OpenCage, Google Maps)
- Generates a GeoJSON FeatureCollection with user locations
- Provides fallback mechanisms for users without location information
- Handles API rate limits and uses multiple geocoding services

## Prerequisites

Before running the script, make sure you have the following:

- Python 3.x installed
- Required Python packages: `requests`
- API keys for the following services (optional, but recommended for better results):
  - GitHub API
  - Google Maps API
  - OpenCage API

## Setup

1. Clone this repository or download the script.
2. Install the required packages:
   ```
   pip install requests
   ```
3. Set up environment variables for API keys:
   ```
   export GITHUB_TOKEN=your_github_token
   export GOOGLE_MAPS_API_KEY=your_google_maps_api_key
   export OPENCAGE_API_KEY=your_opencage_api_key
   ```

## Usage

1. Prepare a text file (`contributors_list.txt`) with the list of contributors in the following format:
   ```
   Full Name <email@example.com>
   Full Name https://github.com/username
   Full Name
   ```

2. Run the script:
   ```
   python github_user_geolocation.py
   ```

3. The script will generate a GeoJSON file (`geojson_results.json`) containing the locations of the contributors.

## How It Works

1. The script reads the list of contributors from the input file.
2. For each contributor, it attempts to find their GitHub profile using their name, email, or GitHub username.
3. If a GitHub profile is found, the script retrieves the user's location information.
4. The location string is geocoded using multiple services (Nominatim, OpenCage, Google Maps) to obtain coordinates.
5. If geocoding fails or no location is available, the script uses a fallback mechanism to predict a country based on the user's name.
6. The results are compiled into a GeoJSON FeatureCollection.
7. The final GeoJSON is saved to a file.

## Limitations

- The accuracy of the geolocation depends on the information provided in GitHub profiles and the geocoding services used.
- API rate limits may affect the script's performance, especially for large lists of contributors.
- The script uses fallback mechanisms and name-based country prediction, which may not always be accurate.

## Contributing

Contributions to improve the script are welcome. Please feel free to submit issues or pull requests.

## License

This project is open-source and available under the MIT License.
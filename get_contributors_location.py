import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import random

from countries_list import FALLBACK_COUNTRIES as fallback_countries

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
OPENCAGE_API_KEY= os.getenv('OPENCAGE_API_KEY')

NATIONALIZE_API_KEY = os.getenv('NATIONALIZE_API_KEY')

added_countries = {}

def get_random_fallback_location():
    return random.choice(fallback_countries)


def predict_country_from_name(name):
    name_parts = name.split(' ')
    surname = None

    if len(name_parts) > 0:
        surname = name_parts[len(name_parts) - 1]
    else:
        return None, None

    url = f"https://api.nationalize.io?name={surname}&apikey={NATIONALIZE_API_KEY}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['country']:
                top_country = max(data['country'], key=lambda c: c['probability'])
                country_code = top_country['country_id']
                return country_code
        return None, None
    except requests.exceptions.RequestException as e:
        return None, None

def get_coordinates_by_country_code(country_code):
    country_coordinates = {c['code']: c for c in fallback_countries}
    return country_coordinates.get(country_code, None)

def create_fallback_geojson(full_name, properties):
    # Try to predict the country from the full name
    country_code = predict_country_from_name(full_name)

    if country_code:
        fallback_location = get_coordinates_by_country_code(country_code)
        if fallback_location:
            # Change the lat a bit so as points don't fall in the same place
            if country_code in added_countries.keys():
                added_countries[country_code] += 1
                lat = (float(fallback_location['lat']) +
                       ( 0.001 * added_countries[country_code]))
                lat = round(lat, 5)
            else:
                added_countries[country_code] = 1
                lat = fallback_location['lat']
            return {
                "type": "Feature",
                "properties": {
                    "Name": full_name,
                    "Committer": properties.get("committer", ""),
                    "Username": properties.get("username", ""),
                    "Country": fallback_location['country'],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [fallback_location["lon"], lat],
                }

            }
    return None

def extract_email_website_github(line):
    parts = line.split()
    if len(parts) > 2:
        third_part = parts[-1].strip('<>')
        return third_part
    return None

def is_email(s):
    return '@' in s

def is_github_account(s):
    return 'github.com' in s


# Function to handle rate limits
def handle_rate_limit(response):
    if (response.status_code == 403 and
            'X-RateLimit-Remaining' in response.headers):
        rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
        if rate_limit_remaining == 0:
            reset_time = int(response.headers['X-RateLimit-Reset'])
            wait_time = reset_time - int(time.time())
            print(f"Rate limit reached, waiting for {wait_time} seconds...")
            time.sleep(wait_time)
            return True
    return False

def search_github_user_by_name(full_name):
    url = f"https://api.github.com/search/users?q={full_name}+in:fullname"
    headers = {"Authorization": f"token {GITHUB_TOKEN}" \
        if GITHUB_TOKEN else None}

    while True:
        response = requests.get(url, headers=headers)
        if handle_rate_limit(response):
            continue

        if response.status_code == 200:
            search_results = response.json()
            if search_results["total_count"] > 0:
                return search_results["items"][0]
            else:
                return None
        else:
            return None

def search_github_user_by_email(email):
    url = f"https://api.github.com/search/users?q={email}+in:email"
    headers = {"Authorization": f"token {GITHUB_TOKEN}" \
        if GITHUB_TOKEN else None}

    while True:
        response = requests.get(url, headers=headers)
        if handle_rate_limit(response):
            continue

        if response.status_code == 200:
            search_results = response.json()
            if search_results["total_count"] > 0:
                return search_results["items"][0]  # Return the first result
            else:
                return None
        else:
            return None


# Function to get a user's detailed profile using their username
def get_github_user(username):
    url = f"https://api.github.com/users/{username}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}" \
            if GITHUB_TOKEN else None
    }

    while True:
        response = requests.get(url, headers=headers)
        if handle_rate_limit(response):
            continue

        if response.status_code == 200:
            return response.json()
        else:
            return None


def geocode_nominatim(location_str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": location_str, "format": "json", "limit": 1}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                return {
                    "lat": float(data[0]["lat"]),
                    "lon": float(data[0]["lon"])
                }
            else:
                return None
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None

# OpenCage geocoding
def geocode_opencage(location_str):
    if not OPENCAGE_API_KEY:
        # print("OpenCage API key not provided.")
        return None

    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {"q": location_str, "key": OPENCAGE_API_KEY, "limit": 1}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data and data['results']:
                geometry = data['results'][0]['geometry']
                return {"lat": geometry['lat'], "lon": geometry['lng']}
            else:
                return None
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None

def geocode_google_maps(location_str):
    if not GOOGLE_MAPS_API_KEY:
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location_str, "key": GOOGLE_MAPS_API_KEY}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                location = data['results'][0]['geometry']['location']
                return {"lat": location['lat'], "lon": location['lng']}
            else:
                return None
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None
def geocode_location(location_str, properties):
    # Try Nominatim first
    location = geocode_nominatim(location_str)
    if location:
        return create_geojson(location, properties)

    location = geocode_opencage(location_str)
    if location:
        return create_geojson(location, properties)

    location = geocode_google_maps(location_str)
    if location:
        return create_geojson(location, properties)

    return None

def create_geojson(location, properties):
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {
            "type": "Point",
            "coordinates": [location['lon'], location['lat']]
        }
    }

def location_to_geojson(location_str, properties):
    geocoded_location = geocode_location(location_str, properties)

    if geocoded_location:
        geojson = {
            "type": "Feature",
            "properties": properties,
            "geometry": {
                "type": "Point",
                "coordinates": [
                    geocoded_location['lon'],
                    geocoded_location['lat']
                ]
            }
        }
        return geojson
    else:
        return None


# Function to find and return the user's location in GeoJSON format with extra properties
# Main function to find user details and return GeoJSON
def find_user_location_and_commit_details(full_name, third_part):
    if is_email(third_part):
        user_data = None
    elif is_github_account(third_part):
        username = third_part.split('github.com/')[-1]
        user_data = {"login": username}
    else:
        user_data = None

    if user_data:
        username = user_data.get("login")
        user_profile = None

        if user_profile:
            location = user_profile.get("location")
            properties = {
                "full_name": full_name,
                "username": username,
                "committer": "Yes",
                "first_commit_message": "Initial revision",
                "first_commit_date": "06-07-2002",  # Example commit info
                # "correct_location": True
            }

            if location:
                geojson = location_to_geojson(location, properties)
                if geojson:
                    return geojson
                else:
                    return create_fallback_geojson(full_name, properties)
            else:
                return create_fallback_geojson(full_name, properties)
        else:
            return create_fallback_geojson(full_name, {"full_name": full_name, "committer": "No"})
    else:
        return create_fallback_geojson(full_name, {"full_name": full_name, "committer": "No"})

# Final function to build a FeatureCollection GeoJSON
def build_geojson_feature_collection(file_path):
    entries = read_names_from_file(file_path)
    feature_collection = {"type": "FeatureCollection", "features": []}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(
            find_user_location_and_commit_details,
            name, third_part): name for name, third_part
                   in entries}

        for future in as_completed(futures):
            name = futures[future]
            try:
                geojson_feature = future.result()
                if geojson_feature:
                    feature_collection["features"].append(geojson_feature)
            except Exception as e:
                pass

    return feature_collection


def read_names_from_file(file_path):
    with open(file_path, 'r') as file:
        entries = []
        for line in file:
            line = line.strip()
            if line:
                third_part = extract_email_website_github(line)
                # Remove the last part (email/website/GitHub link)
                name = line.rsplit(' ', 1)[0]
                entries.append((name, third_part or ''))
    return entries


def process_names(file_path):
    entries = read_names_from_file(file_path)
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(
            find_user_location_and_commit_details,
            name, third_part): name for name, third_part
                   in entries}

        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                results.append({name: result})
            except Exception as e:
                results.append({name: {"error": str(e)}})

    return results


file_path = "data/contributors_list.txt"
geojson_results = build_geojson_feature_collection(file_path)

# Write the results to a JSON file
output_file_path = "data/contributors.json"
with open(output_file_path, 'w') as json_file:
    json.dump(geojson_results, json_file, indent=4)

print(f"GeoJSON results saved to {output_file_path}")
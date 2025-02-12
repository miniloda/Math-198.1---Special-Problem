import json
from logging import raiseExceptions

from dotenv import load_dotenv
import os



def convert_single_to_double_quotes(file_path):
    """
    This function reads a JSON Lines file with single-quoted strings,
    converts the single quotes to double quotes, and writes the modified
    JSON Lines file back to disk.

    Parameters:
    file_path (str): The path to the JSON Lines file to be processed.

    Returns:
    None
    """
    file_extension = file_path.split('.')[-1]
    assert file_extension == 'jsonl', f"Invalid file extension: {file_extension}"
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        with open(file_path, 'w') as file:
            for line in lines:
                json_obj = eval(line.replace("'", '"'))
                json_str = json.dumps(json_obj)
                file.write(json_str + '\n')
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    return f"Conversion successful. Modified JSON Lines file saved as {file_path}"

def municipal_coordinates(file_name, municipals, column_names, rewrite_file=False):
    """
    This function takes a list of municipalities, takes each coordinates and writes them to a csv file.
    :param file_name: The name of the file to be written, in csv.
    :param municipals: the list of municipalities
    :param column_names: the names of the columns
    :param rewrite_file: if the file should be rewritten if it already has contents.
    :return: Dictionary with the municipalities and their coordinates.
    """
    import csv
    import requests

    load_dotenv()
    google_api_key = os.environ.get('GOOGLE_API_KEY')
    # Create a dictionary to store the coordinates
    coordinates = {}
    if rewrite_file:
        with open(file_name, mode="w", newline="") as file:
            pass  # This does nothing, effectively clearing the file
    else:
        # Check if the file exists and has content
        try:
            with open(file_name, mode="r") as file:
                if file.read().strip():  # Check if the file has non-empty content
                    raise Exception(
                        f"Content already exists in the file. Set rewrite_file to True to overwrite it."
                    )
        except FileNotFoundError:
            pass  # No file exists, so no action needed

    # Open the file in write mode
    with open(file_name, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Write the column names to the file
        writer.writerow(column_names)

        # Loop through the municipalities
        for municipal in municipals:
            # Get the coordinates of the municipality
            response = requests.get(f"https://maps.googleapis.com/maps/api/geocode/json?address={municipal+'+Iloilo'}&key={google_api_key}")
            data = json.loads(response.text)
            if data:
                lat = data['results'][0]['geometry']['location']['lat']
                lng = data['results'][0]['geometry']['location']['lng']
                coordinates[municipal] = (lat, lng)
                writer.writerow([municipal, lat, lng])

            else:
                coordinates[municipal] = 'Not found'
                writer.writerow([municipal, 'Not found', 'Not found'])

    return coordinates

def get_weather_data(start_date,end_date, lat, long):
   import openmeteo_requests
   import requests_cache
   import pandas as pd
   from retry_requests import retry

   # Setup the Open-Meteo API client with cache and retry on error
   cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
   retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
   openmeteo = openmeteo_requests.Client(session=retry_session)

   # Make sure all required weather variables are listed here
   # The order of variables in hourly or daily is important to assign them correctly below
   url = "https://archive-api.open-meteo.com/v1/archive"
   params = {
       "latitude": lat,
       "longitude": long,
       "start_date": start_date,
       "end_date": end_date,
       "hourly": ["temperature_2m", "relative_humidity_2m"],
       "daily": "precipitation_sum"
   }
   responses = openmeteo.weather_api(url, params=params)

   # Process first location. Add a for-loop for multiple locations or weather models
   response = responses[0]
   print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
   print(f"Elevation {response.Elevation()} m asl")
   print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
   print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

   # Process hourly data. The order of variables needs to be the same as requested.
   hourly = response.Hourly()
   hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
   hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()

   hourly_data = {"date": pd.date_range(
       start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
       end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
       freq=pd.Timedelta(seconds=hourly.Interval()),
       inclusive="left"
   )}

   hourly_data["temperature_2m"] = hourly_temperature_2m
   hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m

   hourly_dataframe = pd.DataFrame(data=hourly_data)

   # Process daily data. The order of variables needs to be the same as requested.
   daily = response.Daily()
   daily_precipitation_sum = daily.Variables(0).ValuesAsNumpy()

   daily_data = {"date": pd.date_range(
       start=pd.to_datetime(daily.Time(), unit="s", utc=True),
       end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
       freq=pd.Timedelta(seconds=daily.Interval()),
       inclusive="left"
   )}

   daily_data["precipitation_sum"] = daily_precipitation_sum

   daily_dataframe = pd.DataFrame(data=daily_data)

   return hourly_dataframe, daily_dataframe


def weather_to_jsonl(municipal_dict, file_name, start_date="2014-01-01", end_date="2024-12-31", date_hourly=3, rewrite_file=False):
    """
    This function retrieves historical weather data from the OpenWeatherMap API for a list of municipalities,
    converts the data into a JSONL format, and saves it to a file.

    Parameters:
    municipal_dict (dict): A dictionary containing the municipalities and their coordinates.
    file_name (str): The name of the file to save the JSONL data.
    start_date (str): The start date for which to retrieve weather data. Default is January 1, 2014.
    end_date (str): The end date for which to retrieve weather data. Default is December 31, 2024.
    date_hourly (int): The th hour of the day to get the weather data. Default is 3 am.
    rewrite_file (bool): Whether to overwrite the file if it already exists. False to append to the file.

    Returns:
    None
    """
    import datetime
    import json
    import os

    # If rewrite_file is True, remove existing file and create a new empty file
    if rewrite_file and os.path.exists(file_name):
        os.remove(file_name)


    # Loop through the municipalities
    for municipality, (lat, lng) in municipal_dict.items():
        # check if municipality already exists in the file
        if os.path.exists(file_name):
            with open(file_name, "r") as file:
                lines = file.readlines()
                if any(municipality in line for line in lines):
                    print(f"{municipality} already exists in the file. Skipping...")
                    continue
        # Get the weather data for the municipality
        hourly_dataframe, daily_dataframe = get_weather_data(start_date, end_date, lat, lng)
        # Filter the data to get the weather at the specified hour
        hourly_data = hourly_dataframe[hourly_dataframe["date"].dt.hour == date_hourly]
        # convert the date of hourly_data and daily_dataframe to YYYY-MM-DD format
        hourly_data["date"] = hourly_data["date"].dt.strftime("%Y-%m-%d")
        daily_dataframe["date"] = daily_dataframe["date"].dt.strftime("%Y-%m-%d")
        # Add a new column to indicate the municipality
        hourly_data["municipality"] = municipality
        # Combine the hourly and daily data
        weather_data = hourly_data.merge(daily_dataframe, on="date", how="left")
        # Convert the weather data to JSON
        weather_json = weather_data.to_json(orient="records", lines=True)
        # Write the JSON data to the file
        with open(file_name, "a") as file:
            file.write(weather_json + "\n")


import os
import json
import datetime
import requests
import pytz
from dotenv import load_dotenv


def get_air_pollution_data(start_date, end_date, lat, lng):
    """
    Fetch historical air pollution data from OpenWeatherMap API.
    """
    load_dotenv()
    API_KEY = os.getenv("OPENWEATHER_API_KEY")

    url = (f"https://api.openweathermap.org/data/2.5/air_pollution/history?lat={lat}&lon={lng}"
           f"&start={start_date}&end={end_date}&appid={API_KEY}")
    response = requests.get(url).json()

    if 'cod' in response:
        raise Exception(f"Error: {response.get('message', 'Unknown error')}")
    print(response)
    return response.get('data', [])  # Returns list of pollution data


def air_pollution_to_jsonl(municipal_dict, file_name, rewrite_file=False):
    """
    Retrieve historical air pollution data for multiple municipalities and save to a JSONL file.
    """
    manila_tz = pytz.timezone("Asia/Manila")
    start_dt = manila_tz.localize(datetime.datetime(2021, 1, 1, 0, 0, 0))
    end_dt = manila_tz.localize(datetime.datetime(2024, 12, 31, 23, 59, 59))
    start_timestamp = int(start_dt.timestamp())
    end_timestamp = int(end_dt.timestamp())

    existing_data = {}
    if os.path.exists(file_name) and not rewrite_file:
        with open(file_name, "r") as file:
            for line in file:
                try:
                    json_data = json.loads(line)
                    municipality = json_data["municipality"]
                    timestamp = json_data["timestamp"]
                    existing_data[municipality] = max(existing_data.get(municipality, start_timestamp), timestamp)
                except json.JSONDecodeError:
                    continue

    with open(file_name, "w" if rewrite_file else "a") as file:
        for municipality, (lat, lng) in municipal_dict.items():
            last_timestamp = existing_data.get(municipality, start_timestamp)

            if last_timestamp >= end_timestamp:
                print(f"Skipping {municipality}, already up to date.")
                continue

            for i in range(last_timestamp, end_timestamp, 86400):
                pollution_data = get_air_pollution_data(i, i + 86399, lat, lng)
                print(pollution_data)
                for entry in pollution_data:
                    json_record = {
                        "municipality": municipality,
                        "lat": lat,
                        "lng": lng,
                        "timestamp": entry.get("dt"),
                        "components": entry.get("components", {}),
                    }
                    file.write(json.dumps(json_record) + "\n")
                    print(f"Data saved for {municipality} on {datetime.datetime.utcfromtimestamp(json_record['timestamp'])}")
    print("Data saved to", file_name)


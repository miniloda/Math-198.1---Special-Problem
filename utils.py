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

def get_weather_data(date, lat, long):
    """
    Retrieves historical weather data from the OpenWeatherMap API.

    Args:
        time (int): The date and time in Unix time format for which to retrieve weather data.
        lat (str): The latitude of the location for which to retrieve weather data.
        long (str): The longitude of the location for which to retrieve weather data.

    Returns: dict: The JSON response from the OpenWeatherMap API containing the historical weather data.
    """
    import requests
    import os
    load_dotenv()
    API_KEY = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/3.0/onecall/day_summary?lat={lat}&lon={long}&date={date}&appid={API_KEY}"
    response = requests.get(url).json()
    if 'cod' in response.keys():
        raise Exception(f"Error: {response['message']}")
    data = response['data'][0]
    return data




def weather_to_jsonl(municipal_dict, file_name, rewrite_file=False):
    """
    This function retrieves historical weather data from the OpenWeatherMap API for a list of municipalities,
    converts the data into a JSONL format, and saves it to a file.

    Parameters:
    municipal_dict (dict): A dictionary containing the municipalities and their coordinates.
    file_name (str): The name of the file to save the JSONL data.
    rewrite_file (bool): Whether to overwrite the file if it already exists. False to append to the file.

    Returns:
    None
    """
    import datetime
    import json
    import os
    # Define start and end timestamps
    start_timestamp = 1388534400  # January 1, 2014
    end_timestamp = 1706659200  # January 31, 2024

    # If rewrite_file is True, remove existing file and create a new empty file
    if rewrite_file and os.path.exists(file_name):
        os.remove(file_name)

    # Track last processed municipality and timestamp
    last_processed_municipal = None
    last_processed_timestamp = start_timestamp

    # Check the last recorded entry in the file (if it exists)
    if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
        with open(file_name, "r") as file:
            lines = file.readlines()
            if lines:
                try:
                    last_entry = json.loads(lines[-1])  # Load the last JSONL entry
                    last_processed_municipal = last_entry.get("municipal", None)
                    last_processed_timestamp = last_entry.get("date", start_timestamp)
                except json.JSONDecodeError:
                    print("Error reading last line of the file. Starting fresh.")

    # Iterate through the municipalities
    for municipal, (lat, lon) in municipal_dict.items():
        # If the last municipality was the same and we already reached the end date, skip
        if last_processed_municipal == municipal and last_processed_timestamp >= end_timestamp:
            continue

        # If continuing from a partially processed municipality, adjust start timestamp
        start_time = last_processed_timestamp if last_processed_municipal == municipal else start_timestamp

        for timestamp in range(start_time, end_timestamp, 86400):  # Increment by 1 day (86400 seconds)
            date_str = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')

            # Fetch weather data (assuming get_weather_data function exists)
            weather_data = get_weather_data(date_str, lat, lon)
            weather_data['municipal'] = municipal
            weather_data['date'] = timestamp  # Store timestamp in the data

            # Append to file in JSONL format
            with open(file_name, "a") as file:
                file.write(json.dumps(weather_data) + "\n")

        # Reset last processed timestamp for the next municipality
        last_processed_timestamp = start_timestamp

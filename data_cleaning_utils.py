import pandas as pd

def get_merged_df(municipal_name):
    print(f"Cleaning data for {municipal_name}")
    municipal_df = pd.read_csv(f'data/dengue/DOH/{municipal_name}.csv', skiprows=2)
    weather_df = clean_weather_data(municipal_name)
    #drop columns with nan
    municipal_df.dropna(axis=1, inplace=True)
    # create a Year-Week column
    municipal_df['Year-Week'] = municipal_df['Year'].astype(int).astype(str) + '-' + municipal_df['Week'].astype(int).astype(str) + '-0'
    municipal_df['Year-Week'] = pd.to_datetime(municipal_df['Year-Week'], format='%Y-%W-%w')
    print(municipal_df.head())
    # merge weather_df and municipal_df
    df_merged = pd.merge_asof(weather_df.sort_values('Year-Week'), municipal_df.sort_values('Year-Week'), on='Year-Week')
    df_merged.dropna(inplace=True)
    # create a dataframe with weekly aggregation
    df_merged_weekly = df_merged.groupby(['Year-Week']).agg({'Temperature': 'mean', 'Humidity': 'mean', 'Precipitation': 'sum', 'Cases': 'mean'}).reset_index()
    # merge the weekly data with
    df_population = clean_population_data(municipal_name)
    df_merged_weekly = pd.merge_asof(df_merged_weekly.sort_values('Year-Week'), df_population.sort_values('Year'), on='Year-Week')
    # Add Year column
    df_merged_weekly['Year'] = df_merged_weekly['Year-Week'].dt.year
    # Add Month column
    df_merged_weekly['Month'] = df_merged_weekly['Year-Week'].dt.month
    # Add Week column
    df_merged_weekly['Week'] = df_merged_weekly['Year-Week'].dt.isocalendar().week
    # save the merged dataframe to a csv file
    df_merged_weekly.to_csv(f'data/Merged Data/{municipal_name}_merged.csv', index=False)
    print(f"Data for {municipal_name} has been cleaned and saved to data/Merged Data/{municipal_name}_merged.csv")

def clean_weather_data(municipal_name):
    weather_df = pd.read_json("municipal_weather_data.jsonl", lines=True)
    weather_df = weather_df.rename(columns={"temperature_2m": "Temperature", "relative_humidity_2m": "Humidity", "precipitation_sum": "Precipitation", "date": "Date"})
    # convert date to datetime
    weather_df['Date'] = pd.to_datetime(weather_df['Date'], format="%Y-%m-%d")
    weather_df['Week'] = weather_df['Date'].dt.isocalendar().week
    weather_df['Year'] = weather_df['Date'].dt.isocalendar().year
    # create a Year-Week column
    weather_df['Year-Week'] = weather_df['Year'].astype(str) + '-' + weather_df['Week'].astype(str) + '-1'
    weather_df['Year-Week'] = pd.to_datetime(weather_df['Year-Week'], format='%Y-%W-%w')
    # Filter weather_df to the municipality only
    weather_df = weather_df[weather_df["municipality"] == municipal_name]

    return weather_df

def clean_population_data(municipal_name):
    # Read the population data
    df_population = pd.read_csv('population_data_complete.csv')
    # Filter the population data to the municipality only
    df_population = df_population[df_population["Municipal"] == municipal_name]
    years = [2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2014]
    population = []
    for year in years:
        # Get the population for the year
        population.append(df_population[str(year)].values[0])
    # Create a new dataframe with the population data
    df_population = pd.DataFrame({'Year': years, 'Population': population})
    df_population['Year-Week'] = pd.to_datetime(df_population['Year'], format='%Y')
    # Create a Year-Week column

    return df_population

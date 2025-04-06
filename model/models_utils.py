import pandas as pd
from sklearn.preprocessing import StandardScaler
import numpy as np
import matplotlib.pyplot as plt
import os
def prepare_dataframe(data_, features, target, date_col, n_ahead):

    # Select relevant columns
    rel_col = features + [target] + [date_col]
    data = data_[rel_col]


    # Define lags
    env_lags = [1,2,3,4]   #2-week lag for environment features
    cases_lag = range(n_ahead, 12)  # 1 to 11 week lags for target variable

    # Create lagged features for environment and target variables
    for lag in env_lags:
        for feature in features:
            data[f'{feature}_lag_{lag}'] = data[feature].shift(lag)

    for lag in cases_lag:
        data[f'{target}_lag_{lag}'] = data[target].shift(lag)
    # Remove any rows with missing values due to lagging
    data = data.dropna()
    #data = pd.get_dummies(data, columns=['month'])
    #for lag in cases_lag:
    # scaling the cases lag to Standard Scaling
    #    data[f'{target}_lag_{lag}'] = StandardScaler().fit_transform(np.array(data[f'{target}_lag_{lag}']).reshape(-1,1))
    #    print(data[f'{target}_lag_{lag}'].head())
    for lag in env_lags:
        for feature in features:
            data[f'{feature}_lag_{lag}'] = StandardScaler().fit_transform(np.array(data[f'{feature}_lag_{lag}']).reshape(-1,1))
    return data

import pandas as pd
import os
import matplotlib.pyplot as plt

def save_data(municipal_name, n_week_ahead, MSE, MAE, predictions, actual):
    # Save the evaluation metrics to a CSV file
    evaluations = pd.DataFrame({
        'n_week_ahead': [n_week_ahead],
        'MSE': [MSE],
        'MAE': [MAE]
    })
    # Create a directory for the municipal if it doesn't exist
    if not os.path.exists(f"output/CSV/{municipal_name}"):
        os.makedirs(f"output/CSV/{municipal_name}")
    evaluations.to_csv(f"output/CSV/{municipal_name}/evaluation_{n_week_ahead}_week_ahead.csv", index=False)

    # Save the predictions and actual values to a CSV file
    predictions_df = pd.DataFrame({
        'predictions': predictions,
        'actual': actual[(actual["Year-Week"].dt.year >= 2023) & (actual["Year-Week"].dt.year <= 2024)]['Cases']
    })

    predictions_df.to_csv(f"output/CSV/{municipal_name}/predictions_{n_week_ahead}_week_ahead.csv", index=False)

    # Make a plot of the predictions and actual values
    fig, ax = plt.subplots(1, 2, figsize=(20, 5))
    ax[0].plot(actual['Year-Week'], actual['Cases'], label='Actual Cases')
    ax[0].plot(actual[(actual['Year-Week'].dt.year >= 2023) & (actual['Year-Week'].dt.year <= 2024)]['Year-Week'], predictions, color='red', label=f'{n_week_ahead}-week ahead')
    ax[0].tick_params(labelrotation=45)
    ax[0].legend()
    ax[1].plot(actual[(actual['Year-Week'].dt.year >= 2023) & (actual['Year-Week'].dt.year <= 2024)]['Year-Week'], actual[(actual['Year-Week'].dt.year >= 2023) & (actual['Year-Week'].dt.year <= 2024)]['Cases'], label='Actual Cases')
    ax[1].plot(actual[(actual['Year-Week'].dt.year >= 2023) & (actual['Year-Week'].dt.year <= 2024)]['Year-Week'], predictions, color='red', label=f'{n_week_ahead}-week ahead')
    ax[1].tick_params(labelrotation=45)
    ax[1].legend()
    plt.suptitle('Comparing Actual and Predicted')

    # Save the plot to a file
    if not os.path.exists(f"output/plots/{municipal_name}"):
        os.makedirs(f"output/plots/{municipal_name}")
    plt.savefig(f"output/plots/{municipal_name}/predictions_{n_week_ahead}_week_ahead.png")
    plt.close()

def save_feat_imp(municipal,n_week_ahead, feature_importance_dict):
    # Create a DataFrame from the feature importance dictionary
    feature_importance_df = pd.DataFrame(feature_importance_dict.items(), columns=['Feature', 'Importance'])
    # Sort the DataFrame by importance
    feature_importance_df = feature_importance_df.sort_values(by='Importance', ascending=False)
    # Save the DataFrame to a CSV file
    if not os.path.exists(f"output/CSV/{municipal}"):
        os.makedirs(f"output/CSV/{municipal}")
    feature_importance_df.to_csv(f"output/CSV/{municipal}/feature_importance_{n_week_ahead}_week_ahead.csv", index=False)
    # Make a bar plot of the feature importance
    plt.figure(figsize=(10, 6))
    plt.barh(feature_importance_df['Feature'], feature_importance_df['Importance'])
    plt.xlabel('Importance')
    plt.ylabel('Feature')
    plt.title('Feature Importance')
    plt.tight_layout()
    # Save the plot to a file
    if not os.path.exists(f"output/plots/{municipal}"):
        os.makedirs(f"output/plots/{municipal}")
    plt.savefig(f"output/plots/{municipal}/feature_importance_{n_week_ahead}_week_ahead.png")
    plt.close()

from flask import Flask, render_template
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
from pytrends.request import TrendReq
from pytrends.exceptions import TooManyRequestsError
from datetime import datetime, timedelta

app = Flask(__name__)

# Initialize Pytrends
pytrends = TrendReq(hl='en-US', tz=360)

def fetch_trend_data(keyword, start_date, end_date):
    timeframe = f'{start_date} {end_date}'
    pytrends.build_payload([keyword], timeframe=timeframe)
    data = pytrends.interest_over_time()
    return data.drop('isPartial', axis=1) if not data.empty else None

def fetch_with_retries(keyword, start_date, end_date, retries=5, backoff=60):
    for attempt in range(retries):
        try:
            return fetch_trend_data(keyword, start_date, end_date)
        except TooManyRequestsError:
            print(f"Rate limit hit, sleeping for {backoff} seconds... (Attempt {attempt + 1}/{retries})")
            time.sleep(backoff)
            backoff *= 2
    print("Failed to retrieve data after multiple attempts. Please try again later.")
    return None

@app.route('/')
def index():
    # Define the keyword and calculate dates
    keyword = "west indies vs south africa"
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')

    previous_end_date = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')
    previous_start_date = (datetime.today() - timedelta(days=14)).strftime('%Y-%m-%d')

    # Fetch data
    current_data = fetch_with_retries(keyword, start_date, end_date)
    previous_data = fetch_with_retries(keyword, previous_start_date, previous_end_date)

    if current_data is not None and previous_data is not None:
        current_volume = current_data.mean()[keyword]
        previous_volume = previous_data.mean()[keyword]

        growth = ((current_volume - previous_volume) / previous_volume) * 100 if previous_volume != 0 else float('inf')
        
        volume_text = f"{int(current_volume)}"
        growth_text = f"{int(growth)}X+"

        # Set the seaborn style for better aesthetics
        sns.set(style="whitegrid")

        # Create a figure for rendering
        plt.figure(figsize=(12, 8))
        sns.lineplot(data=current_data, palette="tab10", linewidth=2.5)
        plt.fill_between(current_data.index, current_data[keyword], color='blue', alpha=0.1)

        plt.xlabel('Date', fontsize=14, color='gray')
        plt.ylabel('Search Interest', fontsize=14, color='gray')
        plt.title('Google Search Interest Over the Last 7 Days', fontsize=18, weight='bold', color='blue')
        plt.xticks(rotation=45, ha='right', fontsize=12)
        plt.yticks(fontsize=12)
        plt.text(current_data.index[-1], current_data[keyword].max(), f'Volume: {volume_text}\nGrowth: +{growth_text}', 
                 horizontalalignment='right', size='medium', color='green', weight='semibold')
        plt.legend([keyword], loc='upper left', fontsize=12)

        # Save plot to a BytesIO object
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf8')

        return render_template('index.html', plot_url=plot_url)
    else:
        return "Could not retrieve sufficient data for both periods."

if __name__ == "__main__":
    app.run(debug=True)

import csv
import os
import openai
import json
import requests
import time
from dotenv import load_dotenv
import logging
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

# Load environment variables
open_ai_key = os.getenv("OPENAI_API_KEY")
logger.info(f"OPENAI_API_KEY: {open_ai_key}\n")

# Set up OpenAI client
openai.api_key = open_ai_key
# Set up constants
BASE_URL = "https://api.openai.com/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {open_ai_key}",
}

# Set up the model
MODEL = "gpt-3.5-turbo"

# Set up the prompt
PROMPT = """
I would like you to create a profile for the player based on the following information:
- Name: {name}
- POS: Quarterback
- TD: 35
- YDS: 4500
"""

def create_profile(name):
    """
    Create a profile for a player based on their stats and name.
    """
    # Set up the data for the API call
    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT.format(name=name),
            }
        ],
        "temperature": 0.7,
    }
    
    # Make the request to the OpenAI API
    response = requests.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=data)
    
    # Check the response status
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        logger.error(f"Error: {response.status_code} - {response.text}")
        return None

# Function to handle OpenAI API calls with retry logic
def call_openai_with_retries(prompt, max_retries=5):
    """Retries API calls with exponential backoff to handle rate limits."""
    for attempt in range(max_retries):
        try:
            # Use the new OpenAI ChatCompletion API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Adjusted to match the script model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return response.choices[0].message['content'].strip()  # Updated to reflect correct response structure
        except openai.error.RateLimitError as e:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)  # Wait before retrying
        except openai.error.APIError as e:
            logger.error(f"OpenAI API Error: {e}")
            return "Error: OpenAI API request failed."
    return "Error: API limit reached."

def main():
    """
    Main function to create a profile for a player based on their name and stats.
    """

    # Query player and generate profile
    name = "Joe Burrow"  # Example player name
    profile = call_openai_with_retries(f"Create a profile for {name}.")
    
    # Print the generated profile
    if profile:
        print(f"Player Profile for {name}:\n{profile}")
    else:
        logger.error(f"Could not generate profile for {name}.")

if __name__ == "__main__":
    main()

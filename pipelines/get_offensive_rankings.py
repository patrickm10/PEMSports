"""
NFL Offensive Stats Analyzer
Author: Patrick Mejia
Date: 2025-06-11
"""

from bs4 import BeautifulSoup
import logging
import polars as pl
import requests
import re
import os

def rename_duplicate_headers(headers):
    """
    Rename duplicate headers by keeping the first occurrence as-is,
    and prefixing duplicates with 'R_'.

    Example:
    ['PLAYER', 'ATT', 'YDS', 'ATT', 'YDS'] -> ['PLAYER', 'ATT', 'YDS', 'R_ATT', 'R_YDS', 'R_TD']
    """
    seen = set()
    new_headers = []
    for h in headers:
        if h not in seen:
            new_headers.append(h)
            seen.add(h)
        else:
            new_headers.append(f"R_{h}")
    return new_headers

def clean_player_name(name: str) -> str:
    """
    Remove any team abbreviation in parentheses from player name.
    E.g. "Josh Allen (BUF)" or "Josh Allen\n(BUF)" -> "Josh Allen"
    """
    if not isinstance(name, str):
        logging.warning(f"Expected string for player name, got {type(name)}: {name}")
        return name
    clean_name = re.sub(r"\s*\(.*?\)", "", name)
    
    return clean_name.strip()

def get_positional_rankings(position: str, year: int) -> pl.DataFrame:
    """
    Fetches and processes NFL offensive rankings for a given position.

    Args:
        position (str): The position to fetch rankings for (e.g., 'QB', 'RB', 'WR').

    Returns:
        pl.DataFrame: A DataFrame containing the processed rankings.
    """
    position = position.lower()
    url = f"https://www.fantasypros.com/nfl/stats/{position}.php?scoring=PPR&year={year}"
    print(url)
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'table'})
        if not table:
            logging.error(f"No data table found for position: {position}")
            return pl.DataFrame()

        headers = [th.text.strip() for th in table.find_all('th')]

        headers = rename_duplicate_headers(headers)

        player_data = []
        for row in table.find("tbody").find_all("tr"):
            cols = row.find_all("td")
            if not cols:
                continue

            player_info = []
            for idx, col in enumerate(cols):
                text = col.text.strip()
                if idx == 1:
                    text = clean_player_name(text)
                player_info.append(text)
            player_data.append(player_info)

        if not player_data:
            logging.error(f"No player data found for position: {position}")
            return pl.DataFrame()

        if len(headers) != len(player_data[0]):
            logging.error(f"Header length mismatch: {len(headers)} headers but {len(player_data[0])} player data columns")
            return pl.DataFrame()

    except Exception as e:
        logging.error(f"Error fetching data for position {position}: {e}")
        return pl.DataFrame()

    df = pl.DataFrame(player_data, orient="row", schema=headers)
    df = df.filter(pl.col("G")> "0")
    
    # Add year column for historical tracking
    df = df.with_columns(pl.lit(year).alias("Year"))
    
    return df

def calc_fantasy_ppr_points(df, week, position):
    
    """
    Function to calculate fantasy points per reception (PPR) based on the scoring system.
    Args:
        df (DataFrame): A pandas DataFrame containing the player stats.
        Returns:
        df (DataFrame): A pandas DataFrame containing the player stats with PPR points.
        week (int): The week number.
        position (str): The position of the player.
    """
    # ESPN scoring system
    qb_point_system = {
        "YDS": 0.05,
        "TD": 4,
        "INT": -2,
        #TODO: Add rushing stats when available
        # "Rushing Yards": 0.1,
        # "Rushing Touchdowns": 6,
    }
    rb_point_system = { 
        "YDS": 0.1,
        "TD": 6,
        "REC": 1,
        "REC_YDS": 0.1,
        "REC": 6,
        # "ATT": 0.1,
    }
    wr_point_system = {
        "REC": 1,
        "YDS": 0.1,
        "TD": 6,
    }
    te_point_system = {
        "REC": 1,
        "YDS": 0.1,
        "TD": 6,
    }
    k_point_system = {
        "FGM": 3,
        "Field Goals Missed": -1,
        "XPM": 1,
    }

    # Calculate fantasy points for each player based on the scoring system and week
    for index, row in df.iterrows():
        if position == "QB":
            points = (
                row["YDS"] * qb_point_system["YDS"]
                + row["TD"] * qb_point_system["TD"]
                + row["INT"] * qb_point_system["INT"]
            )
        elif position == "RB":
            points = (
                row["YDS"] * rb_point_system["YDS"]
                + row["TD"] * rb_point_system["TD"]
                + row["REC"] * rb_point_system["REC"]
                + row["REC_YDS"] * rb_point_system["REC_YDS"]
            )
        elif position == "WR":
            points = (
                row["YDS"] * wr_point_system["YDS"]
                + row["TD"] * wr_point_system["TD"]
                + row["REC"] * wr_point_system["REC"]
            )
        elif position == "TE":
            points = (
                row["YDS"] * te_point_system["YDS"]
                + row["TD"] * te_point_system["TD"]
                + row["REC"] * te_point_system["REC"]
            )
        elif position == "K":
            points = (
                row.get("FGM", 0) * k_point_system.get("FGM", 0)
                + row.get("Field Goals Missed", 0) * k_point_system.get("Field Goals Missed", 0)
                + row.get("XPM", 0) * k_point_system.get("XPM", 0)
            )
        else:
            points = 0

        df.at[index, f"Week {week} Points"] = points

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DL', 'LB', 'DB']
    positions = ['QB', 'RB', 'WR', 'TE', 'K']
    
    # Create output directory if it doesn't exist
    output_dir = "data/official_rankings/position"
    os.makedirs(output_dir, exist_ok=True)
    
    # Dictionary to store all data for each position
    all_position_data = {pos: [] for pos in positions}

    for year in range(2020, 2026):
        print(f"Fetching rankings for year: {year}")
        for pos in positions:
            print(f"{pos} Rankings for {year}")
            rankings_df = get_positional_rankings(pos, year)
            if not rankings_df.is_empty():
                logging.info(f"Successfully fetched {len(rankings_df)} records for position: {pos} in year: {year}")
                print(f"{rankings_df}\n")
                
                # Add to our collection for this position
                all_position_data[pos].append(rankings_df)
                
                # Write individual year CSV
                # year_output_path = f"{output_dir}/{pos}_{year}.csv"
                # rankings_df.write_csv(year_output_path)
                # print(f"Saved {pos} {year} data to {year_output_path}")
    
    # Combine all years for each position and write historical CSV
    for pos in positions:
        if all_position_data[pos]:
            # Concatenate all dataframes for this position
            combined_df = pl.concat(all_position_data[pos])
            
            # Sort by year and then by rank/performance metric
            if "RK" in combined_df.columns:
                combined_df = combined_df.sort(["Year", "RK"])
            else:
                combined_df = combined_df.sort("Year")
            
            # Write historical data CSV
            historical_output_path = f"{output_dir}/{pos}_historical.csv"
            combined_df.write_csv(historical_output_path)
            print(f"Saved {pos} historical data ({len(combined_df)} total records) to {historical_output_path}")
            
            logging.info(f"Completed processing for {pos}: {len(combined_df)} total records across all years")
                

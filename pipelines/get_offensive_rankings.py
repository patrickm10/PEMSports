"""
NFL Offensive Stats Analyzer
Author: Patrick Mejia
"""

import requests
from bs4 import BeautifulSoup
import logging
from collections import Counter


def get_team_td_stats():
    """
    Function to scrape kicking stats from the NFL website.
    Returns: df (DataFrame): A pandas DataFrame containing the scraped kicking stats.
    """
    url = "https://www.nfl.com/stats/team-stats/offense/scoring/2024/reg/all"
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", class_="d3-o-table")
    headers = [th.get_text().strip() for th in table.find_all("th")]
    player_data = []
    for row in table.find_all("tr")[1:]:  # Skip the header row
        player = [td.get_text().strip() for td in row.find_all("td")]
        player_data.append(player)
    df = pd.DataFrame(player_data, columns=headers)
    return df


def find_best_team_td(df):
    """
    Function to find the best kicker based on a kicker score that incorporates field goal percentage,
    distance ranges, and field goal attempts as a percentage of the top kicker's attempts.
    Args:
        df (DataFrame): A pandas DataFrame containing the kicking stats.
    Returns:
        best_kickers (DataFrame): A pandas DataFrame containing the top kickers ranked by their kicker score.
    """

    # Initialize the weighted score column and ensure FG and Att are integers
    df["Weighted Score"] = 0
    # print(df.columns)
    df["Team"] = df["Team"].str.split().str[0]
    df["Rsh TD"] = df["Rsh TD"].astype(int)
    df["Rec TD"] = df["Rec TD"].astype(int)
    df["Tot TD"] = df["Tot TD"].astype(int)
    df["2-PT"] = df["2-PT"].astype(int)

    df["Score"] = (
        (df["Rsh TD"] * 0.25)
        + (df["Rec TD"] * 0.25)
        + (df["Tot TD"] * 0.4)
        + (df["2-PT"] * 0.1)
    )

    df["Weighted Score"] = (
        (df["Score"] - df["Score"].min()) / (df["Score"].max() - df["Score"].min())
    ) * 100

    # Sort quarterbacks by the composite score in descending order
    best_team_td = df.sort_values(
        by="Weighted Score", ascending=False, ignore_index=True
    ).head(25)

    # Print the top quarterbacks
    # print(best_team_td)

    # Optionally, save the top quarterbacks to a new CSV file
    best_team_td.to_csv("official_team_td_stats.csv", index=False)

    return best_team_td


def separate_names(df):
    """
    Function to separate the first and last names in a DataFrame column.
    Args:
        df (DataFrame): A pandas DataFrame containing the player names.
    Returns:
        df (DataFrame): A pandas DataFrame with separate columns for first and last names.
    """
    # Split the 'Name' column into 'First Name' and 'Last Name'
    df[["First Name", "Last Name"]] = df["Name"].str.split(" ", 1, expand=True)
    df["First Name"] = df["First Name"].str.strip().str.replace(",", "")
    return df



def find_best_kickers():
    """
    Function to find the best kicker based on a kicker score that incorporates field goal percentage,
    distance ranges, and field goal attempts as a percentage of the top kicker's attempts.
    Args:
        df (DataFrame): A pandas DataFrame containing the kicking stats.
    Returns:
        best_kickers (DataFrame): A pandas DataFrame containing the top kickers ranked by their kicker score.
    """
    url = "https://www.fantasypros.com/nfl/stats/k.php?scoring=PPR"

    try:
        # Fetch the page content
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP issues
        soup = BeautifulSoup(response.content, "html.parser")

        # Locate the table
        table = soup.find("table", {"class": "table"})
        if not table:
            print("Table not found on the page.")
            return None

        # Extract headers and rows
        headers = [th.get_text().strip() for th in table.find("thead").find_all("th")]

        player_data = []
        for row in table.find("tbody").find_all("tr"):
            player = [td.get_text().strip() for td in row.find_all("td")]
            if len(player) == len(headers):
                player_data.append(player)

        # Create DataFrame only if player_data is not empty
        if not player_data:
            print("No player data found.")
            return None

        df = pd.DataFrame(player_data, columns=headers)
        df.columns = df.columns.str.strip()  # Clean column names
        # print(df.columns)
        # print(df.head(50))

        # Check if there are duplicate "FG" columns and drop the second one
        if df.columns.tolist().count("FG") > 1:
            # print("Duplicate 'FG' columns found. Keeping the first one.")
            df = df.loc[:, ~df.columns.duplicated()]

        # print("Cleaned DataFrame columns:", df.columns)

        # Convert relevant columns to numeric
        df["FG"] = pd.to_numeric(df["FG"], errors="coerce").fillna(0).astype(int)
        df["FGA"] = pd.to_numeric(df["FGA"], errors="coerce").fillna(0).astype(int)
        df["PCT"] = pd.to_numeric(df["PCT"], errors="coerce").fillna(0).astype(float)
        df["1-19"] = pd.to_numeric(df["1-19"], errors="coerce").fillna(0).astype(int)
        df["20-29"] = pd.to_numeric(df["20-29"], errors="coerce").fillna(0).astype(int)
        df["30-39"] = pd.to_numeric(df["30-39"], errors="coerce").fillna(0).astype(int)
        df["40-49"] = pd.to_numeric(df["40-49"], errors="coerce").fillna(0).astype(int)
        df["50+"] = pd.to_numeric(df["50+"], errors="coerce").fillna(0).astype(int)
        df["FPTS/G"] = (
            pd.to_numeric(df["FPTS/G"], errors="coerce").fillna(0).astype(float)
        )
        df["FPTS"] = pd.to_numeric(df["FPTS"], errors="coerce").fillna(0).astype(float)

        # Calculate a composite score based on weighted stats (you can adjust the weights as needed)
        df["Score"] = (
            (df["FG"] * 0.4)
            + (df["FGA"] * 0.2)
            + (df["PCT"] * 0.2)
            + (df["1-19"] * 0.1)
            + (df["20-29"] * 0.2)
            + (df["30-39"] * 0.1)
            + (df["40-49"] * 0.1)
            + (df["50+"] * 0.1)
            + (df["FPTS/G"] * 0.4)
            + (df["FPTS"] * 0.3)
        )

        # Sort kickers by the composite score in descending order
        # Reset rank based on score
        df["Rank"] = df["Score"].rank(ascending=False, method="min")
        df["Rank"] = df["Rank"].astype(int)

        best_kickers = df.sort_values(
            by="Score", ascending=False, ignore_index=True
        ).head(32)

        df["Score"] = df["Score"].astype(float)
        df["Weighted Score"] = (
            (df["Score"] - df["Score"].min()) / (df["Score"].max() - df["Score"].min())
        ) * 100

        df["Weighted Score"] = df["Weighted Score"].astype(float)

        # Print the top kickers
        # print(best_kickers)

        best_kickers = remove_team_from_player_name(best_kickers)

        # Save to CSV
        best_kickers.to_csv(
            "data/official_rankings/official_kicker_stats.csv", index=False
        )
        print(
            "Top kicker stats saved to 'data/official_rankings/official_kicker_stats.csv'."
        )

        return best_kickers

    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None


def find_best_qbs():
    url = "https://www.fantasypros.com/nfl/stats/qb.php?scoring=PPR"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP issues
        soup = BeautifulSoup(response.content, "html.parser")

        # Locate the table
        table = soup.find("table", {"class": "table"})
        if not table:
            print("Table not found on the page.")
            return None

        # Extract headers and rows
        raw_headers = [
            th.get_text().strip() for th in table.find("thead").find_all("th")
        ]

        # Handle duplicate headers by appending an index to duplicates
        header_counts = Counter()
        headers = []
        for header in raw_headers:
            if header_counts[header]:
                new_header = f"{header}_{header_counts[header]}"
            else:
                new_header = header
            headers.append(new_header)
            header_counts[header] += 1  # Increment counter for duplicate detection

        # print("Processed headers:", headers)

        # Extract player data
        player_data = []
        for row in table.find("tbody").find_all("tr"):
            player = [td.get_text().strip() for td in row.find_all("td")]
            if len(player) == len(headers):  # Ensure row matches headers count
                player_data.append(player)

        # Create DataFrame only if player_data is not empty
        if not player_data:
            print("No player data found.")
            return None

        df = pd.DataFrame(player_data, columns=headers)
        df.columns = df.columns.str.strip()  # Clean column names

        # Identify the correct "YDS" column if duplicates exist
        yds_cols = [col for col in df.columns if "YDS" in col]
        if len(yds_cols) > 1:
            df.rename(
                columns={yds_cols[1]: "R_YDS"}, inplace=True
            )  # Rename second instance
            # print("Duplicate 'YDS' column found and renamed.")

        # Identify the correct TD column if duplicates exist
        td_cols = [col for col in df.columns if "TD" in col]
        if len(td_cols) > 1:
            df.rename(columns={td_cols[1]: "R_TD"}, inplace=True)
            # print("Duplicate 'TD' column found and renamed.")

        # Identify the correct "ATT" column if duplicates exist
        att_cols = [col for col in df.columns if "ATT" in col]
        if len(att_cols) > 1:
            df.rename(columns={att_cols[1]: "R_ATT"}, inplace=True)
            # print("Duplicate 'ATT' column found and renamed.")

        # Ensure we reference the correct "YDS" column
        passing_yds = yds_cols[0] if yds_cols else "YDS"

        # Remove commas from numeric columns
        numeric_cols = ["CMP", passing_yds, "TD", "Y/A", "INT", "FPTS/G", "FPTS"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].str.replace(",", "", regex=True)

        # Convert relevant columns to numeric values
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Ensure data types are correct
        df["CMP"] = df["CMP"].astype(int)
        df[passing_yds] = df[passing_yds].astype(int)
        df["R_YDS"] = df["R_YDS"].astype(int)
        df["TD"] = df["TD"].astype(int)
        df["Y/A"] = df["Y/A"].astype(float)
        df["INT"] = df["INT"].astype(int)
        df["FPTS/G"] = df["FPTS/G"].astype(float)
        df["FPTS"] = df["FPTS"].astype(float)

        # Calculate composite score
        df["Score"] = (
            (df[passing_yds] * 0.4)
            + (df["R_YDS"] * 0.1)
            + (df["TD"] * 0.3)
            + (df["Y/A"] * 0.2)
            - (df["INT"] * 0.1)
            + (df["FPTS/G"] * 0.4)
            + (df["FPTS"] * 0.3)
            + (df["CMP"] * 0.1)
        )

        # Calculate normalized score
        df["Weighted Score"] = (
            (df["Score"] - df["Score"].min()) / (df["Score"].max() - df["Score"].min())
        ) * 100

        # Sort and select top players
        df["Rank"] = df["Score"].rank(ascending=False, method="min")
        df["Rank"] = df["Rank"].astype(int)

        best_qbs = df.sort_values(by="Score", ascending=False, ignore_index=True).head(
            32
        )

        # Remove team names from player names
        best_qbs = remove_team_from_player_name(best_qbs)

        # Save to CSV
        best_qbs.to_csv("data/official_rankings/official_qb_stats.csv", index=False)
        print("Top QB stats saved to 'data/official_rankings/official_qb_stats.csv'.")
        print(best_qbs)

        return best_qbs

    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None


def find_best_rbs():
    """
    Function to find the best running backs based on rushing yards, touchdowns, yards per carry, and fumbles.
    Args:
        df (DataFrame): A pandas DataFrame containing the rushing stats.
        Returns:
        best_rbs (DataFrame): A pandas DataFrame containing the top running backs ranked by a composite score.
    """
    url = "https://www.fantasypros.com/nfl/stats/rb.php?scoring=PPR"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP issues
        soup = BeautifulSoup(response.content, "html.parser")

        # Locate the table
        table = soup.find("table", {"class": "table"})
        if not table:
            print("Table not found on the page.")
            return None

        # Extract headers and rows
        raw_headers = [
            th.get_text().strip() for th in table.find("thead").find_all("th")
        ]

        # Handle duplicate headers by appending an index to duplicates
        header_counts = Counter()
        headers = []
        for header in raw_headers:
            if header_counts[header]:
                new_header = f"{header}_{header_counts[header]}"
            else:
                new_header = header
            headers.append(new_header)
            header_counts[header] += 1  # Increment counter for duplicate detection

        # print("Processed headers:", headers)

        # Extract player data
        player_data = []
        for row in table.find("tbody").find_all("tr"):
            player = [td.get_text().strip() for td in row.find_all("td")]
            if len(player) == len(headers):  # Ensure row matches headers count
                player_data.append(player)

        # Create DataFrame only if player_data is not empty
        if not player_data:
            print("No player data found.")
            return None

        df = pd.DataFrame(player_data, columns=headers)
        df.columns = df.columns.str.strip()  # Clean column names

        # Identify the correct "YDS" column if duplicates exist
        yds_cols = [col for col in df.columns if "YDS" in col]
        if len(yds_cols) > 1:
            df.rename(
                columns={yds_cols[1]: "REC_YDS"}, inplace=True
            )  # Rename second instance
            # print("Duplicate 'YDS' column found and renamed.")

        # Identify the correct TD column if duplicates exist
        td_cols = [col for col in df.columns if "TD" in col]
        if len(td_cols) > 1:
            df.rename(columns={td_cols[1]: "REC_TD"}, inplace=True)
            # print("Duplicate 'TD' column found and renamed.")

        # print("Cleaned DataFrame columns:", df.columns)

        # Remove commas from YDS column (ensure we're working with the correct one)
        # TODO: Add extra dataframe column for rushing and receiving yards
        df["YDS"] = df["YDS"].str.replace(",", "", regex=True)

        # Convert relevant columns to numeric
        df["ATT"] = pd.to_numeric(df["ATT"], errors="coerce").fillna(0).astype(int)
        df["YDS"] = pd.to_numeric(df["YDS"], errors="coerce").fillna(0).astype(int)
        df["TD"] = pd.to_numeric(df["TD"], errors="coerce").fillna(0).astype(int)
        df["REC_YDS"] = (
            pd.to_numeric(df["REC_YDS"], errors="coerce").fillna(0).astype(int)
        )
        df["REC_TD"] = (
            pd.to_numeric(df["REC_TD"], errors="coerce").fillna(0).astype(int)
        )
        df["Y/A"] = pd.to_numeric(df["Y/A"], errors="coerce").fillna(0).astype(float)
        df["FPTS/G"] = (
            pd.to_numeric(df["FPTS/G"], errors="coerce").fillna(0).astype(float)
        )
        df["FPTS"] = pd.to_numeric(df["FPTS"], errors="coerce").fillna(0).astype(float)
        df["FL"] = pd.to_numeric(df["FL"], errors="coerce").fillna(0).astype(int)
        df["REC"] = pd.to_numeric(df["REC"], errors="coerce").fillna(0).astype(int)
        # Calculate composite score
        df["Score"] = (
            (df["YDS"] * 0.45)
            + (df["TD"] * 0.4)
            + (df["Y/A"] * 0.15)
            + (df["FPTS/G"] * 0.3)
            + (df["FPTS"] * 0.2)
        )
        +(df["ATT"] * 0.1)
        -(df["FL"] * 0.1)
        +(df["REC"] * 0.1)
        +(df["REC_YDS"] * 0.1)
        +(df["REC_TD"] * 0.1)

        df["Weighted Score"] = (
            (df["Score"] - df["Score"].min()) / (df["Score"].max() - df["Score"].min())
        ) * 100

        # Sort and select top players
        # Reset rank based on score
        df["Rank"] = df["Score"].rank(ascending=False, method="min")
        df["Rank"] = df["Rank"].astype(int)

        best_rbs = df.sort_values(by="Score", ascending=False, ignore_index=True).head(
            32
        )

        best_rbs = remove_team_from_player_name(best_rbs)

        # Save to CSV
        best_rbs.to_csv("data/official_rankings/official_rb_stats.csv", index=False)
        print("Top RB stats saved to 'data/official_rankings/official_rb_stats.csv'.")

        return best_rbs

    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None


def find_best_tes():
    """
    Function to find the best tight ends based on receiving stats.

    Returns:
        best_tes (DataFrame): A pandas DataFrame containing the top tight ends ranked by a composite score.
    """
    url = "https://www.fantasypros.com/nfl/stats/te.php"

    try:
        # Fetch the page content
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP issues
        soup = BeautifulSoup(response.content, "html.parser")

        # Locate the table
        table = soup.find("table", {"class": "table"})
        if not table:
            print("Table not found on the page.")
            return None

        # Extract headers and rows
        headers = [th.get_text().strip() for th in table.find("thead").find_all("th")]

        player_data = []
        for row in table.find("tbody").find_all("tr"):
            player = [td.get_text().strip() for td in row.find_all("td")]
            if len(player) == len(headers):  # Ensure row matches header count
                player_data.append(player)

        # Create DataFrame only if player_data is not empty
        if not player_data:
            print("No player data found.")
            return None

        df = pd.DataFrame(player_data, columns=headers)
        df.columns = df.columns.str.strip()  # Clean column names
        # print(df.head(50))

        # Check if there are duplicate "YDS" columns and drop the second one
        if df.columns.tolist().count("YDS") > 1:
            # print("Duplicate 'YDS' columns found. Keeping the first one.")
            df = df.loc[
                :, ~df.columns.duplicated()
            ]  # Keep only the first occurrence of each column

        # print("Cleaned DataFrame columns:", df.columns)

        # Remove commas from YDS column (ensure we're working with the correct one)
        df["YDS"] = df["YDS"].str.replace(",", "", regex=True)

        # Convert relevant columns to numeric
        df["REC"] = pd.to_numeric(df["REC"], errors="coerce").fillna(0).astype(int)
        df["YDS"] = pd.to_numeric(df["YDS"], errors="coerce").fillna(0).astype(int)
        df["TD"] = pd.to_numeric(df["TD"], errors="coerce").fillna(0).astype(int)
        df["Y/R"] = pd.to_numeric(df["Y/R"], errors="coerce").fillna(0).astype(float)
        df["LG"] = pd.to_numeric(df["LG"], errors="coerce").fillna(0).astype(int)
        df["20+"] = pd.to_numeric(df["20+"], errors="coerce").fillna(0).astype(int)
        df["FPTS/G"] = (
            pd.to_numeric(df["FPTS/G"], errors="coerce").fillna(0).astype(float)
        )
        df["FPTS"] = pd.to_numeric(df["FPTS"], errors="coerce").fillna(0).astype(float)

        # Calculate composite score
        df["Score"] = (df["REC"] * 0.35) + (df["YDS"] * 0.25) + (df["TD"] * 0.5)
        (
            +(df["Y/R"] * 0.15)
            + (df["LG"] * 0.1)
            + (df["20+"] * 0.1)
            + (df["FPTS/G"] * 0.4)
            + (df["FPTS"] * 0.3)
        )

        df["Weighted Score"] = (
            (df["Score"] - df["Score"].min()) / (df["Score"].max() - df["Score"].min())
        ) * 100

        # Sort and select top players
        # Reset rank based on score
        df["Rank"] = df["Score"].rank(ascending=False, method="min")
        df["Rank"] = df["Rank"].astype(int)
        best_tes = df.sort_values(by="Score", ascending=False, ignore_index=True).head(
            50
        )
        
        best_tes = remove_team_from_player_name(best_tes)

        # Save to CSV
        best_tes.to_csv("data/official_rankings/official_te_stats.csv", index=False)
        print("Top TE stats saved to 'data/official_rankings/official_te_stats.csv'.")

        return best_tes

    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None


def find_best_wrs():
    """
    Function to find the best wide receivers based on receiving yards, receptions, yards per reception, and touchdowns.
    Args:
        df (DataFrame): A pandas DataFrame containing the receiving stats.
    Returns:
        best_wrs (DataFrame): A pandas DataFrame containing the top wide receivers ranked by a composite score.
    """
    url = "https://www.fantasypros.com/nfl/stats/wr.php?scoring=PPR"
    try:
        # Fetch the page content
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP issues
        soup = BeautifulSoup(response.content, "html.parser")

        # Locate the table
        table = soup.find("table", {"class": "table"})
        if not table:
            print("Table not found on the page.")
            return None

        # Extract headers and rows
        headers = [th.get_text().strip() for th in table.find("thead").find_all("th")]

        player_data = []
        for row in table.find("tbody").find_all("tr"):
            player = [td.get_text().strip() for td in row.find_all("td")]
            if len(player) == len(headers):
                player_data.append(player)

        # Create DataFrame only if player_data is not empty
        if not player_data:
            print("No player data found.")
            return None

        df = pd.DataFrame(player_data, columns=headers)
        df.columns = df.columns.str.strip()  # Clean column names
        # print(df.head(50))

        # Check if there are duplicate "YDS" columns and drop the second one
        if df.columns.tolist().count("YDS") > 1:
            # print("Duplicate 'YDS' columns found. Keeping the first one.")
            df = df.loc[:, ~df.columns.duplicated()]

        # print("Cleaned DataFrame columns:", df.columns)

        # Remove commas from YDS column (ensure we're working with the correct one)
        df["YDS"] = df["YDS"].str.replace(",", "", regex=True)

        # Convert relevant columns to numeric
        df["REC"] = pd.to_numeric(df["REC"], errors="coerce").fillna(0).astype(int)
        df["YDS"] = pd.to_numeric(df["YDS"], errors="coerce").fillna(0).astype(int)
        df["TD"] = pd.to_numeric(df["TD"], errors="coerce").fillna(0).astype(int)
        df["Y/R"] = pd.to_numeric(df["Y/R"], errors="coerce").fillna(0).astype(float)
        df["LG"] = pd.to_numeric(df["LG"], errors="coerce").fillna(0).astype(int)
        df["20+"] = pd.to_numeric(df["20+"], errors="coerce").fillna(0).astype(int)

        # Calculate composite score
        df["Score"] = (df["REC"] * 0.35) + (df["YDS"] * 0.25) + (df["TD"] * 0.5)
        +(df["Y/R"] * 0.15)
        +(df["LG"] * 0.1)
        +(df["20+"] * 0.1)

        df["Weighted Score"] = (
            (df["Score"] - df["Score"].min()) / (df["Score"].max() - df["Score"].min())
        ) * 100

        # Sort and select top players
        # Reset rank based on score
        df["Rank"] = df["Score"].rank(ascending=False, method="min")
        df["Rank"] = df["Rank"].astype(int)
        best_wrs = df.sort_values(by="Score", ascending=False, ignore_index=True).head(
            50
        )
        best_wrs = remove_team_from_player_name(best_wrs)

        # Save to CSV
        best_wrs.to_csv("data/official_rankings/official_wr_stats.csv", index=False)
        print("Top WR stats saved to 'data/official_rankings/official_wr_stats.csv'.")

        return best_wrs

    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None


# TODO: Change function to use schedule vs defense stats
def find_best_wr_defense_matchups(df1, df2):
    """
    Function to find the best wide receiver versus defense matchups based on a combination of receiving and defense stats.
    Args:
        df1 (DataFrame): A pandas DataFrame containing the receiving stats.
        df2 (DataFrame): A pandas DataFrame containing the defensive stats.
        Returns:
        best_matchups (DataFrame): A pandas DataFrame containing the top matchups ranked by a composite score.
    """
    # Normalize the scores for each category
    df1["Weighted Score"] = (
        (df1["Weighted Score"] - df1["Weighted Score"].min())
        / (df1["Weighted Score"].max() - df1["Weighted Score"].min())
    ) * 100
    df2["Weighted Score"] = (
        (df2["Weighted Score"] - df2["Weighted Score"].min())
        / (df2["Weighted Score"].max() - df2["Weighted Score"].min())
    ) * 100

    # Combine the scores for receiving and defense
    df1["Combined Score"] = df1["Weighted Score"] + df2["Weighted Score"]

    # Sort matchups by the combined score in descending order
    best_matchups = df1.sort_values(by="Combined Score", ascending=True).head(32)

    # Print the top matchups
    # print(best_matchups)

    # Optionally, save the top matchups to a new CSV file
    best_matchups.to_csv("official_matchup_stats.csv", index=False)

    return best_matchups


# TODO: Change function to use schedule vs defense stats
def find_best_rb_defense_matchups(df1, df2):
    """
    Function to find the best wide receiver versus defense matchups based on a combination of receiving and defense stats.
    Args:
        df1 (DataFrame): A pandas DataFrame containing the receiving stats.
        df2 (DataFrame): A pandas DataFrame containing the defensive stats.
        Returns:
        best_matchups (DataFrame): A pandas DataFrame containing the top matchups ranked by a composite score.
    """
    # Normalize the scores for each category
    df1["Weighted Score"] = (
        (df1["Weighted Score"] - df1["Weighted Score"].min())
        / (df1["Weighted Score"].max() - df1["Weighted Score"].min())
    ) * 100
    df2["Weighted Score"] = (
        (df2["Weighted Score"] - df2["Weighted Score"].min())
        / (df2["Weighted Score"].max() - df2["Weighted Score"].min())
    ) * 100

    # Combine the scores for receiving and defense
    df1["Combined Score"] = df1["Weighted Score"] + df2["Weighted Score"]

    # Sort matchups by the combined score in descending order
    best_matchups = df1.sort_values(by="Combined Score", ascending=True).head(32)

    # Print the top matchups
    # print(best_matchups)

    # Optionally, save the top matchups to a new CSV file
    best_matchups.to_csv("official_matchup_stats.csv", index=False)

    return best_matchups

def remove_team_from_player_name(df):
    """
    Function to remove the team name from the player name.
    Args:
        player_name (str): The player name.
        team_name (str): The team name.
    Returns:
        player_name (str): The player name without the team name.
    """
    df["Player"] = df["Player"].str.replace(r"\(.*?\)", "", regex=True).str.strip()
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



# Set up logging for better error tracking and debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    """
    Main function to scrape and analyze NFL player and team stats.
    """
    print("\n")
    print("----------------------NFL Stats Analysis-----------------------\n")

    # # Scraping Kicking stats
    try:
        print("Scraping kicking stats...")
        top_kickers = find_best_kickers()
        if top_kickers is not None:
            print(top_kickers)  # Print the top kickers
    except Exception as e:
        print(f"An error occurred while scraping kicking stats: {e}")

    # # # Scraping passing stats
    try:
        print("Scraping passing stats...")
        top_qbs = find_best_qbs()
        if top_qbs is not None:
            print(top_qbs)  # Print the top quarterbacks
    except Exception as e:
        print(f"An error occurred while scraping passing stats: {e}")

    # # # Scraping rushing stats
    try:
        print("Scraping rushing stats...")
        top_rbs = find_best_rbs()
        if top_rbs is not None:
            print(top_rbs)  # Print the top running backs
    except Exception as e:
        print(f"An error occurred while scraping rushing stats: {e}")

    # # # Scraping tight end stats
    try:
        print("Scraping tight end stats...")
        top_tes = find_best_tes()
        if top_tes is not None:
            print(top_tes)  # Print the top tight ends
    except Exception as e:
        print(f"An error occurred while scraping tight end stats: {e}")

    # # # Scraping receiving stats
    try:
        print("Scraping receiving stats...")
        top_wrs = find_best_wrs()
        if top_wrs is not None:
            print(top_wrs)  # Print the top wide receivers
    except Exception as e:
        print(f"An error occurred while scraping receiving stats: {e}")


    # Calculate fantasy points for each player based on the scoring system
    # for week in range(1, 18):
    #     top_qbs = calc_fantasy_ppr_points(top_qbs, week)
    # a_kamara_df = pd.read_csv("rb_stats/rb_weekly_stats/Alvin_Kamara_weekly_stats.csv")
    # a_kamara = calc_fantasy_ppr_points(a_kamara_df, 1,"RB")
    # logger.info(a_kamara)

    # Testing Lanchain with a sample question

    # try:
    # #     # Load NFL stats CSV
    #     nfl_stats_df = pd.read_csv("official_qb_stats.csv")

    #     # Query stats (example)
    #     question = "Who had the most passing YDS in the 2023 season?"
    #     result = query_nfl_stats(question, nfl_stats_df)
    #     logger.info(result)

    # except Exception as e:
    #     logger.error(f"An error occurred during execution: {e}")

    # # # exception handling
    # except Exception as e:
    #     logger.error(f"An error occurred during execution: {e}")

    #     # Create player profile (example)
    #     player_name = "Josh Allen"
    #     player_profile = create_player_profile(nfl_stats_df, player_name)

    #     # Print the player profile
    #     print(player_profile)

    # # exception handling
    # except Exception as e:
    #     logger.error(f"An error occurred during execution: {e}")

    # print("Scraping Team TD stats...")
    # team_td_df = get_team_td_stats()
    # top_team_td = find_best_team_td(team_td_df)
    # print(top_team_td)  # Print the top wide receivers
    # print("\n")

    # csv_file = "schedule.csv"

    # Get scores for week 1-18
    # for week in range(1, 18):
    #     nfl_scores = []
    #     nfl_scores = get_nfl_scores(week)
    #     print(nfl_scores)
    #     nfl_scores.to_csv('nfl_official_scores.csv', index=False)
    # nfl_week1 = get_nfl_scores(1)
    # print(nfl_week1)

    # Find the best wide receiver versus defense matchups
    # best_matchups = find_best_wr_defense_matchups(top_wrs, top_defenses_receiving)
    # print("Best Wide Receiver vs. Defense Matchups:")
    # print(best_matchups)  # Print the top matchups
    # print("\n")

    # Find the best running back versus defense matchups
    # best_rb_matchups = find_best_rb_defense_matchups(top_rbs, top_defenses_rushing)
    # print("Best Running Back vs. Defense Matchups:")
    # print(best_rb_matchups)  # Print the top matchups
    # print("\n")

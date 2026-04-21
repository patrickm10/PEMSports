import csv
import os

def clean_csv(file_path, year):
    temp_path = file_path + ".tmp"
    mapping = {
        "WildCard": "19",
        "Wild Card": "19",
        "Division": "20",
        "ConfChamp": "21",
        "Conf. Champ.": "21",
        "SuperBowl": "22",
        "Super Bowl": "22"
    }

    try:
        with open(file_path, "r", encoding="utf-8") as f_in, \
             open(temp_path, "w", encoding="utf-8", newline="") as f_out:
            reader = csv.reader(f_in)
            writer = csv.writer(f_out)
            
            rows = list(reader)
            if not rows:
                print(f"[{year}] Empty file skipping.")
                return

            for i, row in enumerate(rows):
                # Clean up the row - sometimes PFR has empty elements or extra separators
                # If row is shorter than expected, we skip or pad (usually skip malformed tail)
                if not any(row):
                    continue
                
                # Column 8 (index 7) removal for 2018-2023
                if year <= 2023:
                    if len(row) >= 8:
                        # Before: [W, D, D, T, W, @, L, BOX, P, P, Y, T, Y, T]
                        # After:  [W, D, D, T, W, @, L, P, P, Y, T, Y, T]
                        cleaned_row = row[:7] + row[8:]
                    else:
                        cleaned_row = row
                else:
                    cleaned_row = row
                
                # Postseason mapping for 'Week' column (Index 0)
                if len(cleaned_row) > 0:
                    val = cleaned_row[0].strip()
                    if val in mapping:
                        cleaned_row[0] = mapping[val]
                
                # Header Standardizing (first row)
                if i == 0:
                    # [Week, Day, Date, Time, Winner/tie, @, Loser/tie, PtsW, PtsL, YdsW, TOW, YdsL, TOL]
                    # Note: We enforce a standard set of 13 column names.
                    cleaned_row = ["Week", "Day", "Date", "Time", "Winner/tie", "at", "Loser/tie", "PtsW", "PtsL", "YdsW", "TOW", "YdsL", "TOL"]
                
                writer.writerow(cleaned_row)

        os.replace(temp_path, file_path)
        print(f"[{year}] Successfully cleaned and saved.")
        
    except Exception as e:
        print(f"[{year}] Error: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)

def main():
    metadata_dir = "data/nfl_metadata"
    for year in range(2018, 2026):
        file_path = os.path.join(metadata_dir, f"{year}.csv")
        if os.path.exists(file_path):
            clean_csv(file_path, year)
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    main()

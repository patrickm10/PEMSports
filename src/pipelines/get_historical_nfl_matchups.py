import requests
from bs4 import BeautifulSoup
import polars as pl

START_YEAR = 2018
END_YEAR = 2026
historical_years = range(START_YEAR, END_YEAR)

def get_historical_matchups(year: int, session: requests.Session) -> pl.DataFrame | None:
    """
    Return a DataFrame with columns:
    None signals a fetch or parse problem.
    """
    url = f"https://www.pro-football-reference.com/years/2024/games.htm"
    print(f"Getting data from {url}")
    try:
        response = session.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="games")
        rows = table.find_all("tr")[1:] if table else []

        if not rows:
            return None

        data = []
        headers = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]
        for row in rows:
            cols = row.find_all(["th", "td"])
            if not cols or len(cols) != len(headers):
                continue
            data.append([col.get_text(strip=True) for col in cols])

        if not data:
            return None

        df = pl.DataFrame(data, schema=headers)
        return df

    except Exception as exc:
        print(f"Failed {year} {exc}")
        return None

def main() -> None:
    with requests.Session() as session:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        df = get_historical_matchups(2020, session)
        print(df)

if __name__ == "__main__":
    main()

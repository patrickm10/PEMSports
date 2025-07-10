from bs4 import BeautifulSoup
import warnings
import polars as pl

warnings.filterwarnings("ignore")

def scrape_week(driver, year, week, cache):
    url = f"https://www.nfl.com/schedules/{year}/REG{week}/"
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "nfl-c-matchup-strip__left-area"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
    except Exception as e:
        print(f"Week {week} failed to load: {e}")
        return []

    games = []
    for idx, link in enumerate(soup.select("a.nfl-c-matchup-strip__left-area"), 1):
        game_div = link.select_one("div.nfl-c-matchup-strip__game")
        if not game_div:
            continue

        teams = []
        team_divs = game_div.select("div.nfl-c-matchup-strip__team")
        record_divs = game_div.select("div.css-12hprx4-U7")

        for i, td in enumerate(team_divs):
            abbr = td.select_one("span.nfl-c-matchup-strip__team-abbreviation")
            name = td.select_one("span.nfl-c-matchup-strip__team-fullname")
            teams.append({
                "abbreviation": abbr.text.strip() if abbr else None,
                "fullname": name.text.strip() if name else None,
                "record": record_divs[i].text.strip() if i < len(record_divs) else None
            })

        date = link.select_one("span.nfl-c-matchup-strip__date-time")
        tz = link.select_one("span.nfl-c-matchup-strip__date-timezone")
        time = f"{date.text.strip()} {tz.text.strip()}" if date and tz else None

        game_url = f"https://www.nfl.com{link.get('href')}"
        location = scrape_game_location(driver, game_url, cache)

        for team in teams:
            games.append({
                "week": week,
                "game_number": idx,
                "team_abbreviation": team["abbreviation"],
                "team_fullname": team["fullname"],
                "team_record": team["record"],
                "time": time,
                "location": location
            })

    return games

def main(year=2025):
    driver = build_driver()
    location_cache = {}
    all_games = []

    for week in range(1, 19):
        print(f"Scraping week {week}")
        all_games.extend(scrape_week(driver, year, week, location_cache))

    driver.quit()
    df = pl.DataFrame(all_games)
    df.write_csv(f"nfl_schedule_{year}.csv")
    print(df)
    print(f"Saved to nfl_schedule_{year}.csv")

if __name__ == "__main__":
    main()

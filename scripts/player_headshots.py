import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import logging
from typing import List, Dict, Optional
from pathlib import Path
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pipelines.constants import TEAM_MAP, ESPN_NFL_HEADSHOT_COMBINER_URL, ESPN_NFL_HEADSHOT_RAW_URL  # noqa: E402

BASE_DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_PATH = BASE_DATA_DIR / "player_headshots.csv"

HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Frontend/API contract in this repo serves headshots from:
#   repo-root/assets/players/{player_id}.png  ->  /static/players/{player_id}.png
ASSETS_DIR = PROJECT_ROOT / "assets" / "players"
PUBLIC_HEADSHOTS_ROUTE = "/static/players"

def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\s\-]", "", name).strip().replace(" ", "_")

def build_headshot_path(player_id: str) -> str:
    return f"{PUBLIC_HEADSHOTS_ROUTE}/{str(player_id).strip()}.png"

def fetch_roster(team_abbr: str, team_slug: str) -> List[Dict]:
    url = f"https://www.espn.com/nfl/team/roster/_/name/{team_abbr}/{team_slug}"
    resp = requests.get(url, headers=HTTP_HEADERS)
    if resp.status_code != 200:
        logger.error(f"Failed to fetch roster for {team_abbr}: {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    players = []

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            link = cols[1].find("a", href=re.compile(r"/player/_/id/"))
            if not link:
                continue

            href = link.get("href")
            match = re.search(r"/id/(\d+)/([^/]+)", href)
            if match:
                players.append({
                    "player_id": match.group(1),
                    "player_slug": match.group(2),
                    "name": link.text.strip(),
                    "team": team_abbr.upper()
                })

    return players

def build_espn_headshot_url(player_id: str, *, raw: bool = False) -> str:
    template = ESPN_NFL_HEADSHOT_RAW_URL if raw else ESPN_NFL_HEADSHOT_COMBINER_URL
    return template.format(player_id=str(player_id).strip())

def resolve_headshot(player_id: str, timeout: int = 10) -> Optional[str]:
    player_id = str(player_id).strip()
    if not player_id:
        return None

    cdn_url = build_espn_headshot_url(player_id)
    try:
        resp = requests.get(cdn_url, headers=HTTP_HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return cdn_url
        logger.warning(f"ESPN CDN headshot returned status={resp.status_code} for player_id={player_id}")
    except Exception as e:
        logger.warning(f"ESPN CDN headshot lookup failed for player_id={player_id}: {e}")
        return None

    fallback_url = build_espn_headshot_url(player_id, raw=True)
    try:
        resp = requests.get(fallback_url, headers=HTTP_HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return fallback_url
        logger.warning(f"ESPN CDN raw fallback returned status={resp.status_code} for player_id={player_id}")
    except Exception as e:
        logger.warning(f"ESPN CDN raw fallback failed for player_id={player_id}: {e}")

    return None

def download_image(image_url: str, output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / filename

    resp = requests.get(image_url, headers=HTTP_HEADERS, stream=True, timeout=10)
    resp.raise_for_status()

    with open(file_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return file_path

def run_pipeline(limit_teams: List[str] = None, validation_mode: bool = True):
    teams = limit_teams if limit_teams else TEAM_MAP.keys()

    seen_ids = set()
    seen_assets = set()
    rows: List[Dict[str, str]] = []

    for abbr in teams:
        slug = TEAM_MAP[abbr]
        logger.info(f"Processing team: {abbr.upper()}")

        players = fetch_roster(abbr, slug)

        for p in players:
            if p["player_id"] in seen_ids:
                continue
            seen_ids.add(p["player_id"])

            image_url = resolve_headshot(p["player_id"])

            if image_url:
                if image_url in seen_assets:
                    if validation_mode:
                        return
                    continue

                p["asset_id"] = p["player_id"]
                p["image_url"] = image_url
                seen_assets.add(image_url)

                # Store under the location the API serves directly.
                file_name = f"{str(p['player_id']).strip()}.png"
                image_path = download_image(image_url, ASSETS_DIR, file_name)

                p["image_path"] = build_headshot_path(p["player_id"])

                logger.info(f"Resolved {p['name']}: {image_url}")
                logger.info(f"Saved image to: {image_path}")
                logger.info(f"Output file path: {OUTPUT_PATH}")

                rows.append(
                    {
                        "player_id": str(p["player_id"]),
                        "player_slug": str(p.get("player_slug") or ""),
                        "team": str(p.get("team") or ""),
                        "asset_id": str(p.get("asset_id") or ""),
                        "image_url": str(image_url),
                        "image_path": str(p["image_path"]),
                    }
                )

            time.sleep(0.05)
            if validation_mode:
                logger.info("Validation mode processed one player; stopping.")
                break

        if validation_mode and rows:
            break

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "player_id",
                "player_slug",
                "team",
                "asset_id",
                "image_url",
                "image_path",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

if __name__ == "__main__":
    run_pipeline()
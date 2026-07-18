"""Shared utilities for the pipeline scripts."""

import time

import requests
from fake_useragent import UserAgent

_ua = UserAgent()


def fetch_html(url, delay=3.0):
    """Fetch a page from basketball-reference.com.

    Forces UTF-8 decoding -- by default `requests` guesses the response
    encoding and guesses wrong for these pages, which silently mangles
    accented player names (see read_legacy_html for the same corruption
    baked into files scraped the old way). Includes a polite delay so
    scraping doesn't hammer the site.
    """
    headers = {'User-Agent': _ua.random}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    if delay:
        time.sleep(delay)
    return resp.text


def read_legacy_html(path):
    """Read an HTML file scraped by the old notebook pipeline, repairing text corruption.

    The original scraper (`requests.get(url).text`) let requests guess the
    response encoding instead of forcing UTF-8, and it guessed wrong -- so
    every accented player name (e.g. "Dončić") got silently mangled into
    mojibake (e.g. "DonÄ\\x8diÄ\\x87") before the file was ever saved to disk.
    This is the standard round-trip fix: the mangled text is valid UTF-8 bytes
    that were misread as Latin-1, so re-encoding as Latin-1 and decoding as
    UTF-8 recovers the original text.

    Only use this for the legacy GAMES/SCORES/TEAMS files already on disk --
    new scrapes should fetch with the correct encoding in the first place
    (see pipeline/scrape_games.py and pipeline/scrape_teams.py) and should be
    read with plain UTF-8, not this repair.
    """
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    return raw.encode('latin-1').decode('utf-8')

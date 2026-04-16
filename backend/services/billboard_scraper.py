"""
billboard_scraper.py
--------------------
Scrapes OOH (Out-of-Home) advertising listings from adbuq.com.

Uses requests + BeautifulSoup (static HTML, no JS required).
Search URL pattern: https://www.adbuq.com/search-results/?type[0]=TYPE&location[0]=CITY
"""

import re
import os
import ipaddress
import unicodedata
import math
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://www.adbuq.com"
SEARCH_URL = f"{BASE_URL}/search-results/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Map from natural language aliases → adbuq `type[]` values
TYPE_MAP: Dict[str, str] = {
    # airport
    "airport": "airport",
    "airport advertising": "airport",
    # digital umbrella
    "digital": "digital",
    "all digital": "digital",
    "led": "digital",
    "digital billboard": "digital",
    # digital sub-types
    "pole sign": "digital-pole-signs",
    "pole signs": "digital-pole-signs",
    "digital pole": "digital-pole-signs",
    "smd": "smd",
    "digital smd": "smd",
    "mall digital": "inside-mall-digital",
    "mall advertising": "inside-mall-digital",
    "inside mall": "inside-mall-digital",
    # static umbrella
    "static": "static",
    "all static": "static",
    # static sub-types
    "billboard": "billboards",
    "billboards": "billboards",
    "hoarding": "billboards",
    "bridge": "bridge",
    "bridge panel": "bridge",
    "bus shelter": "bus-shelter",
    "bus stop": "bus-shelter",
    "mall static": "inside-mall-static",
    "mopy": "mopy",
    "pole": "pole",
    "wall panel": "wall-panels",
    "wall panels": "wall-panels",
    "wall": "wall-panels",
    # vehicle
    "vehicle": "vehicle-branding",
    "vehicle branding": "vehicle-branding",
    "transit": "vehicle-branding",
    # physical / generic → default to billboards
    "physical": "billboards",
    "outdoor": "billboards",
    "ooh": "billboards",
}

# City display name → adbuq slug (data-ref values).
# Only major cities listed; everything else is slugified automatically.
CITY_MAP: Dict[str, str] = {
    "lahore": "lahore",
    "karachi": "karachi",
    "islamabad": "islamabad",
    "rawalpindi": "rawalpindi",
    "peshawar": "peshawar",
    "gujranwala": "gujranwala",
    "faisalabad": "faisalabad",
    "multan": "multan",
    "hyderabad": "hyderabad",
    "quetta": "quetta",
    "sialkot": "sialkot",
    "abbottabad": "abbottabad",
    "bahawalpur": "bahawalpur",
    "dera ghazi khan": "dera-ghazi-khan",
    "dera ismail khan": "dera-ismail-khan",
    "sargodha": "sargodha",
    "gujrat": "gujrat",
    "sahiwal": "sahiwal",
    "mardan": "mardan",
    "wah cantt": "wah-cantt",
    "wah": "wah",
    "taxila": "taxila",
}

# Approximate city centers (lat, lon) for robust coordinate fallback.
CITY_COORDS: Dict[str, tuple[float, float]] = {
    "islamabad": (33.6844, 73.0479),
    "rawalpindi": (33.5651, 73.0169),
    "lahore": (31.5204, 74.3587),
    "karachi": (24.8607, 67.0011),
    "faisalabad": (31.4504, 73.1350),
    "multan": (30.1575, 71.5249),
    "peshawar": (34.0151, 71.5249),
    "quetta": (30.1798, 66.9750),
    "hyderabad": (25.3960, 68.3578),
    "gujranwala": (32.1877, 74.1945),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _nearest_supported_city(latitude: float, longitude: float, max_distance_km: float = 120.0) -> Optional[str]:
    """Return nearest supported city name for given coordinates."""
    best_city = None
    best_dist = float("inf")
    for city_name, (lat, lon) in CITY_COORDS.items():
        dist = _haversine_km(latitude, longitude, lat, lon)
        if dist < best_dist:
            best_dist = dist
            best_city = city_name
    if best_city and best_dist <= max_distance_km:
        return best_city
    return None


# ---------------------------------------------------------------------------
# Geolocation and "near me" detection
# ---------------------------------------------------------------------------

def detect_near_me_query(query: str) -> bool:
    """
    Detect if the user's query contains "near me" or similar location references.
    
    Examples:
      - "find me billboards near me"
      - "billboards near my location"
      - "advertising nearby"
      - "find me some digital screens close to me"
    """
    query_lower = query.lower().strip()
    near_me_patterns = [
        r"\bnear\s+me\b",
        r"\bnear\s+my\s+location\b",
        r"\bclose\s+to\s+me\b",
        r"\baround\s+me\b",
        r"\bnearly\b",
        r"\bnearby\b",
        r"\bwhere\s+i\s+am\b",
        r"\bmy\s+location\b",
        r"\bmy\s+city\b",
        r"\bhere\b",
    ]
    
    for pattern in near_me_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return True
    return False


def get_user_city_from_ip(client_ip: Optional[str] = None) -> Optional[str]:
    """
    Detect user's city from their IP address using multiple geolocation services.
    
    Parameters
    ----------
    client_ip : str, optional
        The client's IP address. If None, the function will use a public IP detection service.
    
    Returns
    -------
    str or None
        The city name (e.g. "Karachi", "Lahore") or None if detection fails.
    """
    def _is_local_or_private_ip(ip_value: Optional[str]) -> bool:
        if not ip_value:
            return True
        ip_value = ip_value.strip().split(",")[0].strip()
        try:
            ip_obj = ipaddress.ip_address(ip_value)
            return ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local
        except ValueError:
            return True

    try:
        # If no IP provided, get the user's public IP first
        if not client_ip:
            try:
                ip_response = requests.get("https://api.ipify.org?format=json", timeout=2)
                ip_response.raise_for_status()
                client_ip = ip_response.json().get("ip")
            except Exception as e:
                print(f"[BillboardScraper] Failed to detect public IP: {e}")
                return None
        
        if _is_local_or_private_ip(client_ip):
            # If still no valid IP, return None (likely local testing)
            print("[BillboardScraper] Could not determine public user IP for geolocation")
            return None
        
        # Try primary geolocation service: ip-api.com
        try:
            geo_response = requests.get(
                f"http://ip-api.com/json/{client_ip}?fields=city,country",
                timeout=3
            )
            geo_response.raise_for_status()
            data = geo_response.json()
            
            if data.get("status") == "success":
                country = data.get("country", "")
                city = data.get("city", "")
                
                # Verify this is a Pakistani location
                if country and ("pakistan" in country.lower() or "PK" in country):
                    print(f"[BillboardScraper] Detected user location (ip-api): {city}, {country}")
                    return city
        except Exception as e:
            print(f"[BillboardScraper] Primary geolocation service failed: {e}")
        
        # Try fallback service: ipapi.co
        try:
            geo_response = requests.get(
                f"https://ipapi.co/{client_ip}/json/",
                timeout=3
            )
            geo_response.raise_for_status()
            data = geo_response.json()
            
            country_code = data.get("country_code", "")
            city = data.get("city", "")
            
            # Check if Pakistan (country code: PK)
            if country_code.upper() == "PK" and city:
                print(f"[BillboardScraper] Detected user location (ipapi): {city}, Pakistan")
                return city
        except Exception as e:
            print(f"[BillboardScraper] Fallback geolocation service failed: {e}")
        
        print(f"[BillboardScraper] Geolocation successful but location is outside Pakistan")
        return None
            
    except Exception as e:
        print(f"[BillboardScraper] Geolocation failed: {e}")
        return None


def get_city_for_query(query: str, client_ip: Optional[str] = None) -> Optional[str]:
    """
    Determine the city for a billboard search based on user query.
    
    If the query contains "near me" or similar, uses geolocation to find the user's city.
    Otherwise, returns None (letting the LLM extract the city normally).
    
    Parameters
    ----------
    query : str
        The user's query/message
    client_ip : str, optional
        The client's IP address for geolocation
    
    Returns
    -------
    str or None
        The detected city name, or None if not found
    """
    if detect_near_me_query(query):
        print("[BillboardScraper] Detected 'near me' query, using geolocation...")
        detected_city = get_user_city_from_ip(client_ip)
        if detected_city:
            return detected_city
        fallback_city = os.getenv("DEFAULT_BILLBOARD_CITY", "Rawalpindi").strip()
        if fallback_city:
            print(f"[BillboardScraper] Using DEFAULT_BILLBOARD_CITY fallback: {fallback_city}")
            return fallback_city
    return None


def get_city_from_coordinates(latitude: float, longitude: float) -> Optional[str]:
    """Resolve city from browser coordinates using reverse geocoding."""
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "format": "jsonv2",
                "lat": latitude,
                "lon": longitude,
                "accept-language": "en",
            },
            headers={
                "User-Agent": "Brandmate/1.0",
                "Accept": "application/json",
            },
            timeout=4,
        )
        response.raise_for_status()
        data = response.json()
        address = data.get("address", {})
        city = (
            address.get("city")
            or address.get("town")
            or address.get("municipality")
            or address.get("county")
        )

        # Try to map reverse-geocoded locality text to our supported city list
        # (e.g. "Rawalpindi Tehsil" -> "rawalpindi").
        city_candidates = [
            city,
            address.get("city_district"),
            address.get("county"),
            address.get("state_district"),
            address.get("state"),
            data.get("display_name"),
        ]
        for candidate in city_candidates:
            if not candidate:
                continue
            # 1) Direct city mention match against supported names
            matched_city = extract_city_from_text(candidate)
            if matched_city:
                print(f"[BillboardScraper] Resolved city from coordinates: {matched_city}")
                return matched_city

            # 2) Normalize arbitrary locality strings into supported slugs
            normalized_slug = _normalise_city(candidate)
            mapped_city = next((name for name, slug in CITY_MAP.items() if slug == normalized_slug), None)
            if mapped_city:
                print(f"[BillboardScraper] Resolved city from coordinates: {mapped_city}")
                return mapped_city

        country_code = (address.get("country_code") or "").upper()
        if city and (not country_code or country_code == "PK"):
            print(f"[BillboardScraper] Resolved city from coordinates (raw): {city}")
            normalized_slug = _normalise_city(city)
            mapped_city = next((name for name, slug in CITY_MAP.items() if slug == normalized_slug), None)
            if mapped_city:
                print(f"[BillboardScraper] Mapped raw coordinate city to supported city: {mapped_city}")
                return mapped_city

        # Final fallback: nearest known Pakistani city by coordinates.
        nearest_city = _nearest_supported_city(latitude, longitude)
        if nearest_city:
            print(f"[BillboardScraper] Resolved city by nearest coordinate match: {nearest_city}")
            return nearest_city
    except Exception as e:
        print(f"[BillboardScraper] Coordinate reverse geocoding failed: {e}")

    return None


def extract_city_from_text(text: str) -> Optional[str]:
    """Extract a known city name from free-form user text."""
    lowered = (text or "").lower()
    for city in sorted(CITY_MAP.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(city)}\b", lowered):
            return city
    return None


def infer_ad_type_from_text(text: str) -> str:
    """Infer media type from free-form user text using existing normalisation."""
    lowered = (text or "").strip().lower()
    if not lowered:
        return "billboard"
    return _normalise_type(lowered)


def should_trigger_billboard_search(text: str) -> bool:
    """Detect billboard intent even when LLM tool calling fails."""
    lowered = (text or "").lower()
    intent_terms = [
        "billboard", "billboards", "hoarding", "ooh", "outdoor advertising",
        "outdoor ad", "digital screen", "digital billboard", "smd", "pole sign",
        "bus shelter", "bridge panel", "airport advertising", "physical advertising",
    ]
    return any(term in lowered for term in intent_terms) or detect_near_me_query(lowered)


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalise_type(raw: str) -> str:
    """Convert a user-supplied media type string to an adbuq slug."""
    key = raw.strip().lower()
    if key in TYPE_MAP:
        return TYPE_MAP[key]
    # Try substring match
    for alias, slug in TYPE_MAP.items():
        if alias in key or key in alias:
            return slug
    # Fall back to billboards
    return "billboards"


def _normalise_city(raw: str) -> str:
    """Convert a city name to an adbuq location slug."""
    key = raw.strip().lower()
    if key in CITY_MAP:
        return CITY_MAP[key]
    key_ascii = unicodedata.normalize("NFKD", key).encode("ascii", "ignore").decode("ascii").strip()
    if key_ascii in CITY_MAP:
        return CITY_MAP[key_ascii]

    # Heuristic mapping for district/territory style names.
    if "islamabad" in key or "islamabad" in key_ascii:
        return CITY_MAP["islamabad"]
    if "rawalpindi" in key or "rawalpindi" in key_ascii:
        return CITY_MAP["rawalpindi"]
    if "karachi" in key or "karachi" in key_ascii:
        return CITY_MAP["karachi"]
    if "lahore" in key or "lahore" in key_ascii:
        return CITY_MAP["lahore"]

    # Auto-slugify: lowercase, replace spaces/special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", key_ascii or key).strip("-")
    return slug


# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------

def _build_search_url(city_slug: str, type_slugs: List[str], page: int = 1) -> str:
    """Build the adbuq search URL with proper query parameters.

    adbuq uses empty-bracket array notation:
        type[]=billboards&location[]=islamabad
    which URL-encodes to:
        type%5B%5D=billboards&location%5B%5D=islamabad
    """
    params_parts = []
    for t in type_slugs:
        params_parts.append(f"type%5B%5D={t}")
    params_parts.append(f"location%5B%5D={city_slug}")
    query = "&".join(params_parts)

    if page == 1:
        return f"{SEARCH_URL}?{query}"
    else:
        return f"{SEARCH_URL}page/{page}/?{query}"


def _parse_listing_card(card) -> Optional[Dict[str, Any]]:
    """
    Extract structured data from a single adbuq listing card element.

    adbuq.com uses Houzez theme. The card markup looks like:
        <div class="item-wrap item-wrap-no-frame ...">
          <div class="item-header">
            <div class="labels-wrap">  ← promotional labels (hz-label anchors)
            <ul class="item-price-wrap"><li class="item-price"><span class="price">Rs …</span>
            <div class="listing-thumb"><a href="detail_url"><img …>
          <div class="item-body">
            <h2 class="item-title"><a href="detail_url">Title</a>
            <address class="item-address"><span>City</span>
            <ul class="item-amenities">
              <li class="h-size">Size: <span class="hz-figure">60x30</span>
              <li class="h-vc">Zone: <span class="hz-figure">…</span>

    Returns None if the card cannot be parsed.
    """
    result: Dict[str, Any] = {}

    # ── Title & Detail URL ────────────────────────────────────────────────
    title_el = card.find(["h2", "h3"], class_=re.compile(r"item-title|entry-title|listing-title", re.I))
    if not title_el:
        title_el = card.find(["h2", "h3"])
    if title_el:
        a = title_el.find("a")
        if a:
            result["title"] = a.get_text(strip=True)
            result["detail_url"] = a.get("href", "").strip()
        else:
            result["title"] = title_el.get_text(strip=True)
            result["detail_url"] = ""
    else:
        return None  # skip cards without a title

    # ── Price ─────────────────────────────────────────────────────────────
    # adbuq: <ul class="item-price-wrap"><li class="item-price"><span class="price">Rs …
    price_span = card.find("span", class_="price")
    if price_span:
        result["price"] = price_span.get_text(strip=True)
    else:
        price_el = card.find(class_=re.compile(r"item-price|listing-price|property-price", re.I))
        if price_el:
            result["price"] = price_el.get_text(separator=" ", strip=True)
        else:
            card_text = card.get_text(" ", strip=True)
            price_match = re.search(r"Rs[\s,\d]+(?:/\w+)?", card_text)
            result["price"] = price_match.group(0).strip() if price_match else "Contact for price"

    # ── Location / City ───────────────────────────────────────────────────
    # adbuq: <address class="item-address"><i …></i><span>Islamabad</span></address>
    addr_el = card.find("address", class_=re.compile(r"item-address", re.I))
    if not addr_el:
        addr_el = card.find("address")
    if addr_el:
        span = addr_el.find("span")
        result["city"] = span.get_text(strip=True) if span else addr_el.get_text(strip=True)
    else:
        loc_el = card.find(class_=re.compile(r"listing-location|property-location", re.I))
        result["city"] = loc_el.get_text(strip=True) if loc_el else ""

    # ── Promotional Labels ────────────────────────────────────────────────
    # adbuq: <a class="hz-label label label-color-…">Discounted Price</a>
    # Target hz-label anchors directly to avoid duplicates from nested containers.
    label_els = card.find_all("a", class_=re.compile(r"hz-label", re.I))
    if label_els:
        labels = list(dict.fromkeys(el.get_text(strip=True) for el in label_els if el.get_text(strip=True)))
    else:
        label_els = card.find_all(class_=re.compile(r"label-color-", re.I))
        labels = list(dict.fromkeys(el.get_text(strip=True) for el in label_els if el.get_text(strip=True)))
    result["labels"] = labels

    # ── Dimensions / Size ─────────────────────────────────────────────────
    # adbuq: <li class="h-size …">Size: <span class="hz-figure">60x30</span>
    size_li = card.find("li", class_=re.compile(r"h-size", re.I))
    if size_li:
        hz_fig = size_li.find(class_=re.compile(r"hz-figure", re.I))
        result["dimensions"] = hz_fig.get_text(strip=True) if hz_fig else size_li.get_text(strip=True)
    else:
        card_text = card.get_text(" ", strip=True)
        dim_match = re.search(r"\b\d+\s*x\s*\d+\b", card_text, re.I)
        result["dimensions"] = dim_match.group(0).strip() if dim_match else ""

    # ── Zone / Codes ──────────────────────────────────────────────────────
    # adbuq: <li class="h-vc …">Zone: <span class="hz-figure">6O0FH , KEQWX</span>
    zone_li = card.find("li", class_=re.compile(r"h-vc", re.I))
    if zone_li:
        hz_fig = zone_li.find(class_=re.compile(r"hz-figure", re.I))
        zone_text = hz_fig.get_text(strip=True) if hz_fig else zone_li.get_text(strip=True)
        result["zone"] = zone_text
        code_matches = re.findall(r"[A-Z0-9]{4,6}", zone_text)
        result["adbuq_codes"] = list(set(code_matches)) if code_matches else []
    else:
        card_text = card.get_text(" ", strip=True)
        code_matches = re.findall(r"\b[A-Z0-9]{5}\b", card_text)
        result["zone"] = ""
        result["adbuq_codes"] = list(set(code_matches)) if code_matches else []

    # ── Image URL ─────────────────────────────────────────────────────────
    # adbuq: <div class="listing-thumb"><a …><img data-src="…">
    thumb_div = card.find(class_=re.compile(r"listing-thumb", re.I))
    img_el = thumb_div.find("img") if thumb_div else card.find("img")
    if img_el:
        img_url = img_el.get("data-src") or img_el.get("src") or ""
        if img_url and "svg" not in img_url.lower() and "data:image" not in img_url.lower():
            result["image_url"] = img_url
        else:
            result["image_url"] = ""
    else:
        el_with_bg = card.find(style=re.compile(r"background-image", re.I))
        if el_with_bg:
            bg_match = re.search(r"url\(['\"]?([^'\")\s]+)['\"]?\)", el_with_bg.get("style", ""))
            result["image_url"] = bg_match.group(1) if bg_match else ""
        else:
            result["image_url"] = ""

    # ── Source ────────────────────────────────────────────────────────────
    result["source"] = "adbuq.com"
    result["source_url"] = "https://www.adbuq.com"

    return result


def scrape_billboards(
    city: str,
    ad_type: str = "billboard",
    max_pages: int = 2,
) -> Dict[str, Any]:
    """
    Scrape billboard listings from adbuq.com.

    Parameters
    ----------
    city : str
        City name (e.g. "Lahore", "Karachi").
    ad_type : str
        Media type in natural language (e.g. "digital", "billboard", "pole signs").
        Comma-separated for multiple types (e.g. "billboard,digital").
    max_pages : int
        Number of result pages to scrape (each page = ~15 listings).

    Returns
    -------
    dict with keys:
        - results: list of billboard dicts
        - total_found: int (from page header if available)
        - city: normalised city
        - ad_type: normalised ad type slug(s)
        - search_url: the URL used
        - error: str (only present if something went wrong)
    """
    # Normalise inputs
    city_slug = _normalise_city(city)
    if not city_slug:
        return {
            "results": [],
            "total_found": 0,
            "city": "",
            "ad_type": ad_type,
            "search_url": "",
            "error": "Could not resolve city for search. Please provide a valid Pakistani city name.",
        }
    type_slugs = [_normalise_type(t.strip()) for t in ad_type.split(",")]
    type_slugs = list(dict.fromkeys(type_slugs))  # deduplicate preserving order

    all_results: List[Dict[str, Any]] = []
    first_url = _build_search_url(city_slug, type_slugs, page=1)
    total_found: Optional[int] = None

    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        for page in range(1, max_pages + 1):
            url = _build_search_url(city_slug, type_slugs, page=page)
            print(f"[BillboardScraper] Fetching page {page}: {url}")

            try:
                resp = session.get(url, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"[BillboardScraper] Request error on page {page}: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract total count from page header (e.g. "1485 OOH Media Found")
            if total_found is None:
                count_el = soup.find(string=re.compile(r"\d+\s+OOH Media Found", re.I))
                if count_el:
                    m = re.search(r"(\d+)", count_el)
                    if m:
                        total_found = int(m.group(1))

            # ── Find listing cards ─────────────────────────────────────────
            # adbuq wraps each listing in a div.item-wrap inside either:
            #   • <article class="…"> (Houzez default), or
            #   • <li class="listing-item …"> / <div class="item-wrap …">
            # Strategy: look for .item-wrap divs first (most reliable), then
            # fall back to <article> tags.
            cards = soup.find_all(
                lambda tag: tag.name in ("div", "article", "li")
                and tag.has_attr("class")
                and any("item-wrap" in c for c in tag["class"])
            )

            if not cards:
                # Fallback 1: Houzez <article class="property-item …">
                cards = soup.find_all(
                    "article",
                    class_=re.compile(r"property-item|property_item|listing", re.I),
                )

            if not cards:
                # Fallback 2: any <article> tag
                cards = soup.find_all("article")

            if not cards:
                print(f"[BillboardScraper] No listing cards found on page {page}.")
                break

            page_results = []
            seen_urls: set = set()
            for card in cards:
                parsed = _parse_listing_card(card)
                if parsed and parsed.get("title"):
                    url_key = parsed.get("detail_url", "") or parsed.get("title", "")
                    if url_key in seen_urls:
                        continue  # adbuq renders each card twice (list + map view)
                    seen_urls.add(url_key)
                    page_results.append(parsed)

            print(f"[BillboardScraper] Page {page}: parsed {len(page_results)} listings.")
            all_results.extend(page_results)

            # Stop if no results on this page (end of pagination)
            if not page_results:
                break

            # Check if Load More / next page exists
            has_next = soup.find("a", string=re.compile(r"Load More|Next", re.I))
            if not has_next and page < max_pages:
                # Also check for pagination links
                next_pg = soup.find("a", class_=re.compile(r"next", re.I))
                if not next_pg:
                    break

    except Exception as e:
        return {
            "results": all_results,
            "total_found": total_found,
            "city": city_slug,
            "ad_type": ", ".join(type_slugs),
            "search_url": first_url,
            "error": str(e),
        }

    return {
        "results": all_results,
        "total_found": total_found,
        "city": city_slug,
        "ad_type": ", ".join(type_slugs),
        "search_url": first_url,
    }


def enrich_with_contact(results: List[Dict[str, Any]], top_n: int = 5, timeout: int = 6) -> None:
    """
    Fetch detail pages for the first *top_n* results and inject the
    ``contact`` field in-place.  Results beyond *top_n* are left unchanged.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    for r in results[:top_n]:
        url = r.get("detail_url", "")
        if not url:
            continue
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            detail_wrap = soup.find("div", class_=re.compile(r"property-detail-wrap", re.I))
            if detail_wrap:
                for li in detail_wrap.find_all("li"):
                    strong = li.find("strong")
                    span = li.find("span")
                    if strong and span:
                        key = strong.get_text(strip=True).rstrip(":")
                        if key.lower() == "contact":
                            val = span.get_text(strip=True)
                            if val:
                                r["contact"] = val
                            break
        except Exception as e:
            print(f"[BillboardScraper] Could not fetch contact for {url}: {e}")


def format_billboard_results(data: Dict[str, Any], top_n: int = 5) -> str:
    """
    Format scraped billboard data into a readable markdown-style string
    suitable for returning to the user as a chat response.

    Parameters
    ----------
    data  : dict returned by scrape_billboards()
    top_n : maximum number of listings to show inline (default 5).
            Any remaining results are linked to adbuq.com.
    """
    results = data.get("results", [])
    city = data.get("city", "").replace("-", " ").title()
    ad_type = data.get("ad_type", "").replace("-", " ").title()
    total = data.get("total_found")
    search_url = data.get("search_url", "")
    error = data.get("error")

    if error and not results:
        return (
            f"❌ Sorry, I couldn't fetch billboard listings from adbuq.com. "
            f"Error: {error}\n\n"
            f"You can search manually at: {search_url}"
        )

    header = f"## 🏙️ Billboard Listings in {city}"
    if ad_type:
        header += f" ({ad_type})"
    if total is not None:
        header += f"\n**{total} total listings found** on adbuq.com"
    shown_count = min(len(results), top_n)
    header += f"\n*Showing top {shown_count} results | [View all on adbuq.com]({search_url})*\n"

    if not results:
        return (
            header + "\n\nNo listings found for this search. "
            "Try a different city or media type, or browse directly at adbuq.com."
        )

    # Only show the top N results inline
    display_results = results[:top_n]
    remaining = len(results) - len(display_results)
    # If total_found is known and larger, use that for the redirect label
    total_remaining = (total - len(display_results)) if (total and total > len(display_results)) else remaining

    lines = [header]
    for i, r in enumerate(display_results, 1):
        title = r.get("title", "Unnamed Billboard")
        price = r.get("price", "Contact for price")
        city_r = r.get("city", city)
        dims = r.get("dimensions", "")
        url = r.get("detail_url", "")
        img = r.get("image_url", "")
        labels = r.get("labels", [])
        codes = r.get("adbuq_codes", [])
        zone = r.get("zone", "")
        contact = r.get("contact", "")

        label_str = " | ".join(f"🏷️ {l}" for l in labels) if labels else ""

        lines.append(f"\n### {i}. [{title}]({url})")
        if label_str:
            lines.append(label_str)
        lines.append(f"- 📍 **Location:** {city_r}")
        lines.append(f"- 💰 **Price:** {price}")
        if dims:
            lines.append(f"- 📐 **Size:** {dims} ft")
        if contact:
            lines.append(f"- 📞 **Contact:** {contact}")
        if img:
            proxy_img = f"http://localhost:8000/api/image-proxy?url={img}"
            lines.append(f"\n![{title}]({proxy_img})")
        if url:
            lines.append(f"- 🔗 [View Details]({url})")

    # Redirect block for remaining listings
    lines.append("\n---")
    if total_remaining and total_remaining > 0:
        lines.append(
            f"### 🔎 {total_remaining:,} more listing(s) available"
        )
        lines.append(
            f"Browse all results directly on adbuq.com — Pakistan's largest OOH media marketplace:\n"
            f"👉 **[View all {city} listings on adbuq.com]({search_url})**"
        )
    else:
        lines.append(f"*Data sourced from [adbuq.com]({search_url}) — Pakistan's OOH media marketplace.*")
    lines.append(f"*Contact adbuq.com: +92 328 020 111 3 | support@adbuq.com*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Detail-page scraper
# ---------------------------------------------------------------------------

def scrape_billboard_detail(detail_url: str) -> Dict[str, Any]:
    """
    Fetch and parse a single adbuq.com billboard detail page.

    Extracts:
      - title           : page <h1> inside div.page-title
      - images          : all gallery images (houzez-gallery-img)
      - description     : plain-text traffic / description block
      - details         : dict of the "Details" section fields
                          (OOH Media ID, Size, Contact, Zone, Availability date)
      - address         : dict with Address, City, State/Province, Country
      - google_maps_url : direct Google Maps link from the "Open on Google Maps" button
      - latitude        : from the embedded map data-map JSON attribute
      - longitude       : from the embedded map data-map JSON attribute
      - detail_url      : the URL that was scraped
      - error           : present only if something went wrong

    Parameters
    ----------
    detail_url : str
        Full URL of the billboard detail page, e.g.
        https://www.adbuq.com/billboards/billboard-at-hazara-motorway-islamabad/
    """
    result: Dict[str, Any] = {"detail_url": detail_url}

    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        resp = session.get(detail_url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        result["error"] = str(e)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Title ────────────────────────────────────────────────────────────
    # <div class="page-title me-4"><h1>Billboard At …</h1></div>
    page_title_div = soup.find("div", class_=re.compile(r"page-title", re.I))
    if page_title_div:
        h1 = page_title_div.find("h1")
        result["title"] = h1.get_text(strip=True) if h1 else page_title_div.get_text(strip=True)
    else:
        h1 = soup.find("h1")
        result["title"] = h1.get_text(strip=True) if h1 else ""

    # ── Gallery Images ───────────────────────────────────────────────────
    # <img class="houzez-gallery-img …" data-lazy="…" src="…">
    gallery_imgs = soup.find_all("img", class_=re.compile(r"houzez-gallery-img", re.I))
    images = []
    seen_imgs: set = set()
    for img in gallery_imgs:
        url = img.get("data-lazy") or img.get("src") or ""
        if url and "svg" not in url and "data:image" not in url and url not in seen_imgs:
            seen_imgs.add(url)
            images.append(url)
    result["images"] = images

    # ── Description ──────────────────────────────────────────────────────
    # <div class="property-description-wrap …"><div class="description-content"><p>…
    desc_wrap = soup.find("div", class_=re.compile(r"property-description-wrap", re.I))
    if desc_wrap:
        desc_content = desc_wrap.find("div", class_=re.compile(r"description-content", re.I))
        target = desc_content if desc_content else desc_wrap
        # Extract clean text, preserving line breaks around <br> / <p>
        for br in target.find_all("br"):
            br.replace_with("\n")
        raw = target.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        description = re.sub(r"\n{3,}", "\n\n", raw).strip()
        result["description"] = description if description else ""
    else:
        result["description"] = ""

    # ── Details section ──────────────────────────────────────────────────
    # <div class="property-detail-wrap …">
    #   <ul class="list-lined"><li><strong>OOH Media ID</strong><span>71689</span>
    details: Dict[str, str] = {}
    detail_wrap = soup.find("div", class_=re.compile(r"property-detail-wrap", re.I))
    if detail_wrap:
        for li in detail_wrap.find_all("li"):
            strong = li.find("strong")
            span = li.find("span")
            if strong and span:
                key = strong.get_text(strip=True).rstrip(":")
                # Use the anchor text if present (e.g. "login to view date"), else span text
                a_tag = span.find("a")
                val = a_tag.get_text(strip=True) if a_tag else span.get_text(strip=True)
                # Strip internal JS placeholder tokens
                if val and "PLACEHOLDER" not in val and val:
                    details[key] = val
                elif a_tag:
                    details[key] = a_tag.get_text(strip=True)
    result["details"] = details

    # Convenience shortcuts from details
    result["ooh_media_id"] = details.get("OOH Media ID", "")
    result["size"] = details.get("Size", "")
    result["contact"] = details.get("Contact", "")
    result["zone"] = details.get("Zone", "")
    result["availability_date"] = details.get("Availability date", "")

    # ── Address section ──────────────────────────────────────────────────
    # <div class="property-address-wrap …">
    #   <ul><li><strong>Address:</strong><span>…</span>
    address: Dict[str, str] = {}
    addr_wrap = soup.find("div", class_=re.compile(r"property-address-wrap", re.I))
    if addr_wrap:
        for li in addr_wrap.find_all("li"):
            strong = li.find("strong")
            span = li.find("span")
            if strong and span:
                key = strong.get_text(strip=True).rstrip(":")
                val = span.get_text(strip=True)
                if key and val:
                    address[key] = val

        # Google Maps button: <a class="hz-btn-map" href="https://maps.google.com/…">
        maps_btn = addr_wrap.find("a", class_=re.compile(r"hz-btn-map", re.I))
        result["google_maps_url"] = maps_btn.get("href", "") if maps_btn else ""

        # Lat / lng / price from data-map JSON on the map div
        map_div = addr_wrap.find(attrs={"data-map": True})
        if map_div:
            try:
                import json
                map_data = json.loads(map_div["data-map"])
                result["latitude"] = map_data.get("latitude", "")
                result["longitude"] = map_data.get("longitude", "")
                result["price"] = map_data.get("pricePin", "")
            except (json.JSONDecodeError, KeyError):
                result["latitude"] = ""
                result["longitude"] = ""
                result["price"] = ""
        else:
            result["latitude"] = ""
            result["longitude"] = ""
            result.setdefault("price", "")

    # Price: primary source is pricePin in data-map JSON (already set above).
    # Fallback: <li class="item-price …"><span class="price">Rs …</span>
    if not result.get("price"):
        price_li = soup.find("li", class_=re.compile(r"item-price", re.I))
        if price_li:
            price_span = price_li.find("span", class_="price")
            result["price"] = price_span.get_text(strip=True) if price_span else ""
        else:
            price_span = soup.find("span", class_="price")
            result["price"] = price_span.get_text(strip=True) if price_span else ""

    result["address"] = address

    result["source"] = "adbuq.com"
    result["source_url"] = "https://www.adbuq.com"
    return result


def format_billboard_detail(data: Dict[str, Any]) -> str:
    """
    Format a scraped billboard detail page into a readable markdown string
    suitable for returning to the user as a chat response.
    """
    if data.get("error") and not data.get("title"):
        return (
            f"Could not fetch billboard details.\n"
            f"Error: {data['error']}\n"
            f"Try opening directly: {data.get('detail_url', '')}"
        )

    lines = []

    title = data.get("title", "Billboard Details")
    lines.append(f"## {title}")
    lines.append(f"*Source: [adbuq.com]({data.get('detail_url', '')})*\n")

    if data.get("price"):
        lines.append(f"**Price:** {data['price']}")

    # Key details
    details = data.get("details", {})
    if details:
        lines.append("\n### Details")
        field_order = ["OOH Media ID", "Size", "Zone", "Contact", "Availability date"]
        shown = set()
        for field in field_order:
            if field in details:
                lines.append(f"- **{field}:** {details[field]}")
                shown.add(field)
        # Any remaining fields not in the ordered list
        for k, v in details.items():
            if k not in shown:
                lines.append(f"- **{k}:** {v}")

    # Address
    address = data.get("address", {})
    if address:
        lines.append("\n### Address")
        for k, v in address.items():
            lines.append(f"- **{k}:** {v}")
    if data.get("google_maps_url"):
        lines.append(f"- [Open on Google Maps]({data['google_maps_url']})")
    lat, lng = data.get("latitude", ""), data.get("longitude", "")
    if lat and lng:
        lines.append(f"- **Coordinates:** {lat}, {lng}")

    # Description
    if data.get("description"):
        lines.append("\n### Description")
        lines.append(data["description"])

    # Images
    images = data.get("images", [])
    if images:
        lines.append(f"\n### Images ({len(images)})")
        for i, img_url in enumerate(images, 1):
            lines.append(f"{i}. {img_url}")

    return "\n".join(lines)

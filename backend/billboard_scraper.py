"""
billboard_scraper.py
--------------------
Scrapes OOH (Out-of-Home) advertising listings from adbuq.com.

Uses requests + BeautifulSoup (static HTML, no JS required).
Search URL pattern: https://www.adbuq.com/search-results/?type[0]=TYPE&location[0]=CITY
"""

import re
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
    # Auto-slugify: lowercase, replace spaces/special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
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


def format_billboard_results(data: Dict[str, Any]) -> str:
    """
    Format scraped billboard data into a readable markdown-style string
    suitable for returning to the user as a chat response.
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
    header += f"\n*Showing {len(results)} results | [View all on adbuq.com]({search_url})*\n"

    if not results:
        return (
            header + "\n\nNo listings found for this search. "
            "Try a different city or media type, or browse directly at adbuq.com."
        )

    lines = [header]
    for i, r in enumerate(results, 1):
        title = r.get("title", "Unnamed Billboard")
        price = r.get("price", "Contact for price")
        city_r = r.get("city", city)
        dims = r.get("dimensions", "")
        url = r.get("detail_url", "")
        img = r.get("image_url", "")
        labels = r.get("labels", [])
        codes = r.get("adbuq_codes", [])
        zone = r.get("zone", "")

        label_str = " | ".join(f"🏷️ {l}" for l in labels) if labels else ""

        lines.append(f"\n### {i}. [{title}]({url})")
        if label_str:
            lines.append(label_str)
        lines.append(f"- 📍 **Location:** {city_r}")
        lines.append(f"- 💰 **Price:** {price}")
        if dims:
            lines.append(f"- 📐 **Size:** {dims} ft")
        if zone:
            lines.append(f"- 🗺️ **Zone:** {zone}")
        if codes:
            lines.append(f"- 🔖 **Adbuq Codes:** {', '.join(codes)}")
        if img:
            lines.append(f"- 🖼️ **Image:** {img}")
        if url:
            lines.append(f"- 🔗 [View Details]({url})")

    lines.append(f"\n---\n*Data sourced from [adbuq.com]({search_url}) — Pakistan's OOH media marketplace.*")
    lines.append(f"*Contact adbuq.com: +92 328 020 111 3 | support@adbuq.com*")

    return "\n".join(lines)

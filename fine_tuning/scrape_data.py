"""
Khaadi Multi-Category Image Scraper

This scraper organizes downloaded images into folders based on clothing categories.
Folder structure: data/Winter/Men, data/Winter/Women, data/Summer/Men, data/Summer/Women

HOW TO USE:
1. Update the URL_CONFIG section below with your desired URLs
2. Run the script: python scrape_data.py
3. Images will be automatically organized into appropriate folders

EXAMPLE URLs you might want to use:
- Winter Men: https://pk.khaadi.com/men-winter/
- Winter Women: https://pk.khaadi.com/women-winter/
- Summer Men: https://pk.khaadi.com/men-summer/
- Summer Women: https://pk.khaadi.com/women-summer/
"""

import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
from datetime import datetime

def _extract_url_from_element(elem, base_url, attr_priority):
    """Try multiple attributes or style background-image to get an image URL."""
    # First, check if this is a custom element (like image-element) that contains an img tag
    try:
        if elem.tag_name.lower() == "image-element":
            # Look for img tags inside the image-element
            child_imgs = elem.find_elements(By.TAG_NAME, "img")
            if child_imgs:
                # Recursively extract URL from the first child img
                return _extract_url_from_element(child_imgs[0], base_url, attr_priority)
    except Exception:
        pass
    
    # Background-image in style
    style = elem.get_attribute("style") or ""
    if "background-image" in style:
        import re
        m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
        if m:
            u = m.group(1)
            return u if u.startswith("http") else urljoin(base_url, u)

    # Attribute priority
    for attr in (attr_priority or []):
        val = elem.get_attribute(attr)
        if not val:
            continue
        if "srcset" in attr or attr == "data-srcset":
            parts = [p.strip() for p in val.split(",") if p.strip()]
            if parts:
                candidate = parts[-1].split()[0]
                return candidate if candidate.startswith("http") else urljoin(base_url, candidate)
        if val:
            return val if val.startswith("http") else urljoin(base_url, val)

    # Fallback to src
    val = elem.get_attribute("src")
    if val:
        return val if val.startswith("http") else urljoin(base_url, val)
    return None

def _collect_image_urls(driver, base_url, selectors):
    """Collect image URLs on the current page using provided selectors."""
    sel = selectors or {}
    attr_priority = sel.get("attr_priority", ["data-src", "data-srcset", "srcset", "src"])
    includes = sel.get("url_includes") or []
    excludes = sel.get("url_excludes") or []

    urls = set()

    try:
        elements = []
        if sel.get("product_cards"):
            cards = driver.find_elements(By.CSS_SELECTOR, sel["product_cards"])
            for card in cards:
                try:
                    imgs = card.find_elements(By.CSS_SELECTOR, sel.get("image_elements", "img"))
                    elements.extend(imgs)
                except Exception:
                    continue
        else:
            # Get all elements matching the selector
            elements = driver.find_elements(By.CSS_SELECTOR, sel.get("image_elements", "img"))
            
            # Also try to find image-element tags specifically if not already included
            if "image-element" not in sel.get("image_elements", ""):
                try:
                    image_elements = driver.find_elements(By.TAG_NAME, "image-element")
                    elements.extend(image_elements)
                except Exception:
                    pass

        for el in elements:
            try:
                u = _extract_url_from_element(el, base_url, attr_priority)
                if not u:
                    continue
                if includes and not any(inc in u for inc in includes):
                    continue
                if excludes and any(exc in u for exc in excludes):
                    continue
                urls.add(u)
            except Exception:
                continue
    except Exception:
        pass

    return urls

def create_folder_structure():
    """Create organized folder structure for clothing categories"""
    base_folders = ["Winter", "Summer"]
    gender_folders = ["Men", "Women"]
    
    for season in base_folders:
        season_path = os.path.join("data", season)
        os.makedirs(season_path, exist_ok=True)
        
        for gender in gender_folders:
            gender_path = os.path.join(season_path, gender)
            os.makedirs(gender_path, exist_ok=True)
    
    print("Created folder structure:")
    print("data/")
    for season in base_folders:
        print(f"  {season}/")
        for gender in gender_folders:
            print(f"    {gender}/")

def setup_driver():
    """Set up Chrome driver with options for headless browsing"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # Reduce harmless Google service errors in logs (optional)
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    # More stealth options for sites that block bots
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        # Automatically download and manage ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # Hide webdriver property to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        print("Please make sure you have Google Chrome browser installed.")
        return None

def scroll_page_to_end(driver, max_scrolls=50, base_url=None, selectors=None):
    """Scroll current page to the end to load all dynamic content and return found image URLs"""
    logger = logging.getLogger(__name__)
    sel = selectors or {}

    previous_image_count = 0
    scroll_count = 0
    no_new_content_count = 0
    current_urls = set()

    while scroll_count < max_scrolls:
        # Scroll to bottom of page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for content to load

        # Check for "Load More" button and click it if present
        try:
            load_more_selectors = [
                "show-more", "load-more", "btn-load-more", "loadmore",
                "pagination-load-more", "infinite-load-more"
            ]

            load_more_btn = None
            for selector in load_more_selectors:
                try:
                    load_more_btn = driver.find_element(By.CLASS_NAME, selector)
                    if load_more_btn.is_displayed() and load_more_btn.is_enabled():
                        break
                except NoSuchElementException:
                    continue

            if load_more_btn and load_more_btn.is_displayed() and load_more_btn.is_enabled():
                driver.execute_script("arguments[0].click();", load_more_btn)
                time.sleep(3)  # Wait for new content
                logger.info(f"Clicked 'Load More' button (scroll {scroll_count + 1})")
        except Exception as e:
            logger.debug(f"No load more button found: {e}")

        # Check if new images have loaded using configurable selectors
        current_urls = _collect_image_urls(driver, base_url or driver.current_url, sel)
        current_image_count = len(current_urls)

        logger.info(f"Scroll {scroll_count + 1}: Found {current_image_count} image URLs on current page")

        if current_image_count == previous_image_count:
            no_new_content_count += 1
            if no_new_content_count >= 3:  # Stop if no new content for 3 consecutive scrolls
                logger.info("No new content detected after 3 attempts. Page fully loaded.")
                break
        else:
            no_new_content_count = 0

        previous_image_count = current_image_count
        scroll_count += 1

        # Additional scroll to ensure we're at the very bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    return current_urls

def find_next_page_button(driver):
    """Find and return the next page button if it exists"""
    logger = logging.getLogger(__name__)
    
    # Common selectors for next page buttons
    next_button_selectors = [
        # By class name
        ("class", "next"),
        ("class", "pagination-next"),
        ("class", "page-next"),
        ("class", "btn-next"),
        ("class", "arrow-right"),
        ("class", "chevron-right"),
        
        # By text content
        ("xpath", "//a[contains(text(), 'Next')]"),
        ("xpath", "//button[contains(text(), 'Next')]"),
        ("xpath", "//a[contains(text(), 'next')]"),
        ("xpath", "//button[contains(text(), 'next')]"),
        ("xpath", "//a[contains(text(), '→')]"),
        ("xpath", "//a[contains(text(), '>')]"),
        
        # By aria-label
        ("xpath", "//a[@aria-label='Next page']"),
        ("xpath", "//button[@aria-label='Next page']"),
        ("xpath", "//a[@aria-label='Go to next page']"),
        
        # Generic pagination patterns
        ("css", "a.next"),
        ("css", "button.next"),
        ("css", ".pagination .next"),
        ("css", ".pager .next"),
        ("css", ".page-numbers .next"),
    ]
    
    for selector_type, selector in next_button_selectors:
        try:
            if selector_type == "class":
                button = driver.find_element(By.CLASS_NAME, selector)
            elif selector_type == "xpath":
                button = driver.find_element(By.XPATH, selector)
            elif selector_type == "css":
                button = driver.find_element(By.CSS_SELECTOR, selector)
            
            # Check if button is visible and clickable
            if button.is_displayed() and button.is_enabled():
                # Additional check - make sure it's not disabled
                classes = button.get_attribute("class") or ""
                if "disabled" not in classes.lower():
                    logger.info(f"Found next page button with selector: {selector}")
                    return button
                    
        except NoSuchElementException:
            continue
        except Exception as e:
            logger.debug(f"Error checking selector {selector}: {e}")
            continue
    
    return None

def scroll_and_load_content(driver, url, max_scrolls=50, selectors=None):
    """Scroll through pages and load all dynamic content from all pages, returning URL strings."""
    logger = logging.getLogger(__name__)

    logger.info(f"Loading page: {url}")
    driver.get(url)

    sel = selectors or {}
    page_ready_selector = sel.get("page_ready") or sel.get("product_cards") or sel.get("image_elements") or "img"

    # Wait for initial content to load using selector provided or fallback to img
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, page_ready_selector))
        )
        logger.info("Initial content loaded successfully")
    except TimeoutException:
        logger.error("Initial content failed to load - page may have changed structure")
        return []

    all_urls = set()
    page_number = 1

    while True:
        logger.info(f"\n--- Processing Page {page_number} ---")

        # Scroll current page to the end and collect URLs
        page_urls = scroll_page_to_end(driver, max_scrolls, base_url=url, selectors=sel)

        if page_urls:
            new_count_before = len(all_urls)
            all_urls.update(page_urls)
            new_added = len(all_urls) - new_count_before
            logger.info(f"Page {page_number}: Found {len(page_urls)} image URLs, {new_added} new")
            logger.info(f"Total unique image URLs so far: {len(all_urls)}")
        else:
            logger.warning(f"No image URLs found on page {page_number}")

        # Look for next page button
        next_button = find_next_page_button(driver)

        if next_button:
            try:
                logger.info(f"Found next page button, navigating to page {page_number + 1}...")

                # Scroll to the button to make sure it's in view
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(1)

                # Click the next button
                driver.execute_script("arguments[0].click();", next_button)

                # Wait for new page to load
                time.sleep(3)

                # Wait for new content to appear using same selector
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, page_ready_selector))
                    )
                    logger.info(f"Page {page_number + 1} loaded successfully")
                    page_number += 1
                    url = driver.current_url
                except TimeoutException:
                    logger.error("Next page failed to load properly")
                    break

            except Exception as e:
                logger.error(f"Error navigating to next page: {e}")
                break
        else:
            logger.info("No next page button found. Finished processing all pages.")
            break

        # Safety check to prevent infinite loops
        if page_number > 100:  # Reasonable limit
            logger.warning("Reached maximum page limit (100). Stopping.")
            break

    logger.info(f"\nCompleted processing {page_number} pages")
    logger.info(f"Total unique image URLs found across all pages: {len(all_urls)}")
    return list(all_urls)

def download_images(img_elements, base_url, target_folder, category_name):
    """Download images from the collected items (WebElements or URL strings) to specified folder"""
    logger = logging.getLogger(__name__)
    
    # Create target folder
    os.makedirs(target_folder, exist_ok=True)
    logger.info(f"Created/verified '{target_folder}' directory")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    downloaded_count = 0
    failed_count = 0
    
    logger.info(f"Starting download of {len(img_elements)} images for {category_name}...")

    # Find the next available index for new images
    import re
    existing_files = os.listdir(target_folder)
    pattern = re.compile(rf"{re.escape(category_name)}_(\d+)\.jpg$")
    used_indices = set()
    for fname in existing_files:
        m = pattern.match(fname)
        if m:
            used_indices.add(int(m.group(1)))
    next_index = max(used_indices) + 1 if used_indices else 0

    for img in img_elements:
        try:
            img_url = None
            # Support both WebElement and raw URL string
            if hasattr(img, "get_attribute"):
                img_url = img.get_attribute("src")
            elif isinstance(img, str):
                img_url = img
            if not img_url:
                logger.warning(f"Image {next_index}: No src attribute found")
                failed_count += 1
                continue

            if not img_url.startswith("http"):
                img_url = urljoin(base_url, img_url)

            # Download image
            response = requests.get(img_url, headers=headers, timeout=10)
            response.raise_for_status()

            # Generate filename with category prefix, always incrementing index
            filename = os.path.join(target_folder, f"{category_name}_{next_index}.jpg")
            with open(filename, "wb") as f:
                f.write(response.content)

            downloaded_count += 1
            next_index += 1
            if downloaded_count % 10 == 0:
                logger.info(f"Downloaded {downloaded_count} images for {category_name}...")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error downloading image {next_index}: {e}")
            failed_count += 1
            continue
        except IOError as e:
            logger.error(f"File I/O error saving image {next_index}: {e}")
            failed_count += 1
            continue
        except Exception as e:
            logger.error(f"Unexpected error downloading image {next_index}: {e}")
            failed_count += 1
            continue
    
    logger.info(f"Download summary for {category_name}: {downloaded_count} successful, {failed_count} failed")
    return downloaded_count

# Import configuration from external file
try:
    from config import URL_CONFIG
except ImportError:
    print("Error: config.py file not found!")
    print("Please make sure config.py exists in the same directory.")
    print("You can copy the URL_CONFIG section from this file to config.py")
    exit(1)

def update_url_config(category, new_url):
    """Helper function to update URLs programmatically"""
    if category in URL_CONFIG:
        URL_CONFIG[category]["url"] = new_url
        print(f"Updated {category} URL to: {new_url}")
    else:
        print(f"Category '{category}' not found. Available categories: {list(URL_CONFIG.keys())}")

def enable_category(category):
    """Enable a specific category for scraping"""
    if category in URL_CONFIG:
        URL_CONFIG[category]["enabled"] = True
        print(f"✅ Enabled {category}")
    else:
        print(f"Category '{category}' not found. Available categories: {list(URL_CONFIG.keys())}")

def disable_category(category):
    """Disable a specific category from scraping"""
    if category in URL_CONFIG:
        URL_CONFIG[category]["enabled"] = False
        print(f"❌ Disabled {category}")
    else:
        print(f"Category '{category}' not found. Available categories: {list(URL_CONFIG.keys())}")

def enable_only(category):
    """Enable only the specified category and disable all others"""
    if category not in URL_CONFIG:
        print(f"Category '{category}' not found. Available categories: {list(URL_CONFIG.keys())}")
        return
    
    for cat_name in URL_CONFIG.keys():
        URL_CONFIG[cat_name]["enabled"] = (cat_name == category)
    
    print(f"✅ Enabled only {category}, disabled all others")

def enable_all():
    """Enable all categories"""
    for category in URL_CONFIG.keys():
        URL_CONFIG[category]["enabled"] = True
    print("✅ Enabled all categories")

def disable_all():
    """Disable all categories"""
    for category in URL_CONFIG.keys():
        URL_CONFIG[category]["enabled"] = False
    print("❌ Disabled all categories")

def show_current_config():
    """Display current URL configuration"""
    print("\nCurrent URL Configuration:")
    print("=" * 60)
    for category, config in URL_CONFIG.items():
        status = "✅ ENABLED" if config.get('enabled', False) else "❌ DISABLED"
        print(f"{category}: {config['url']}")
        print(f"  Status: {status}")
        print(f"  Folder: {config['folder']}")
        print("-" * 60)
    print("=" * 60)

def setup_logging():
    """Set up logging configuration"""
    log_filename = f"scraper_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Main function to scrape images from multiple Khaadi URLs into organized folders"""
    logger = setup_logging()
    logger.info("Starting Khaadi multi-category scraper...")
    
    # Create organized folder structure
    logger.info("Creating folder structure...")
    create_folder_structure()
    
    # Set up the driver
    logger.info("Setting up Chrome driver...")
    driver = setup_driver()
    if not driver:
        logger.error("Failed to set up Chrome driver. Exiting.")
        return
    
    try:
        overall_start_time = datetime.now()
        logger.info(f"Started scraping at {overall_start_time}")
        
        total_downloaded = 0
        
        # Process each enabled URL configuration
        enabled_categories = {k: v for k, v in URL_CONFIG.items() if v.get('enabled', False)}
        
        if not enabled_categories:
            logger.warning("No categories are enabled! Please set 'enabled': True for at least one category in URL_CONFIG.")
            logger.info("Available categories:")
            for cat_name, cat_config in URL_CONFIG.items():
                status = "ENABLED" if cat_config.get('enabled', False) else "DISABLED"
                logger.info(f"  {cat_name}: {status}")
            return
        
        logger.info(f"Found {len(enabled_categories)} enabled categories to process")
        
        for category_name, config in enabled_categories.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing category: {category_name}")
            logger.info(f"URL: {config['url']}")
            logger.info(f"Target folder: {config['folder']}")
            logger.info(f"{'='*50}")
            
            category_start_time = datetime.now()
            
            # Load all content by scrolling
            logger.info(f"Loading page content for {category_name}...")
            selectors = config.get('selectors') if isinstance(config, dict) else None
            img_elements = scroll_and_load_content(driver, config['url'], selectors=selectors)
            
            if not img_elements:
                logger.warning(f"No images found for {category_name}.")
                continue
            
            logger.info(f"Found {len(img_elements)} images for {category_name}")
            
            # Download images to the specific category folder
            logger.info(f"Starting downloads for {category_name}...")
            downloaded_count = download_images(
                img_elements, 
                config['url'], 
                config['folder'],
                category_name
            )
            
            # Add a delay between categories to be respectful to the server
            if category_name != list(enabled_categories.keys())[-1]:  # Not the last category
                logger.info("Waiting 30 seconds before processing next category...")
                time.sleep(30)
            
            total_downloaded += downloaded_count
            
            category_end_time = datetime.now()
            category_duration = category_end_time - category_start_time
            
            logger.info(f"Completed {category_name}: {downloaded_count} images in {category_duration}")
        
        overall_end_time = datetime.now()
        overall_duration = overall_end_time - overall_start_time
        
        logger.info(f"\n{'='*60}")
        logger.info(f"SCRAPING COMPLETED!")
        logger.info(f"Total images downloaded: {total_downloaded}")
        logger.info(f"Total execution time: {overall_duration}")
        logger.info(f"Images organized in data/ folder by category")
        logger.info(f"{'='*60}")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    
    finally:
        logger.info("Closing browser driver...")
        driver.quit()

def test_single_category(category_name):
    """Test function to scrape only one category"""
    logger = setup_logging()
    logger.info(f"Testing single category: {category_name}")
    
    if category_name not in URL_CONFIG:
        logger.error(f"Category '{category_name}' not found. Available: {list(URL_CONFIG.keys())}")
        return
    
    create_folder_structure()
    
    driver = setup_driver()
    if not driver:
        return
    
    try:
        config = URL_CONFIG[category_name]
        logger.info(f"Testing {category_name} - URL: {config['url']}")
        
        selectors = config.get('selectors') if isinstance(config, dict) else None
        img_elements = scroll_and_load_content(driver, config['url'], selectors=selectors)
        
        if img_elements:
            logger.info(f"Found {len(img_elements)} images for {category_name}")
            downloaded_count = download_images(
                img_elements, 
                config['url'], 
                config['folder'],
                category_name
            )
            logger.info(f"Test completed: {downloaded_count} images downloaded")
        else:
            logger.warning(f"No images found for {category_name}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        driver.quit()

if __name__ == "__main__":
    import sys
    
    # Check if user wants to test single category
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test" and len(sys.argv) > 2:
            # Usage: python scrape_data.py test Winter_Men
            test_single_category(sys.argv[2])
        elif command == "show_config":
            # Usage: python scrape_data.py show_config
            show_current_config()
        elif command == "enable" and len(sys.argv) > 2:
            # Usage: python scrape_data.py enable Winter_Men
            enable_category(sys.argv[2])
        elif command == "disable" and len(sys.argv) > 2:
            # Usage: python scrape_data.py disable Winter_Men
            disable_category(sys.argv[2])
        elif command == "enable_only" and len(sys.argv) > 2:
            # Usage: python scrape_data.py enable_only Summer_Women
            enable_only(sys.argv[2])
        elif command == "enable_all":
            # Usage: python scrape_data.py enable_all
            enable_all()
        elif command == "disable_all":
            # Usage: python scrape_data.py disable_all
            disable_all()
        else:
            print("Usage:")
            print("  python scrape_data.py                        # Run full scraper (enabled categories only)")
            print("  python scrape_data.py test <category>        # Test single category")
            print("  python scrape_data.py show_config            # Show current URLs and status")
            print("")
            print("Category Management:")
            print("  python scrape_data.py enable <category>      # Enable a category")
            print("  python scrape_data.py disable <category>     # Disable a category")
            print("  python scrape_data.py enable_only <category> # Enable only one category")
            print("  python scrape_data.py enable_all             # Enable all categories")
            print("  python scrape_data.py disable_all            # Disable all categories")
            print("")
            print("Available categories:")
            for cat in URL_CONFIG.keys():
                print(f"  - {cat}")
    else:
        # Run the full scraper
        main()

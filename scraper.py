"""
scraper.py

Web scraping module - extracts image URLs from websites
Returns image data in RAM (no disk storage)
"""

import logging
import time
from typing import List, Tuple
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import config

logger = logging.getLogger(__name__)


class WebScraper:
    """Scrapes image URLs from websites using Selenium"""
    
    def __init__(self, headless: bool = None):
        """
        Initialize web scraper
        
        Args:
            headless: Run browser in headless mode (defaults to config)
        """
        self.headless = headless if headless is not None else config.HEADLESS_BROWSER
    
    def scrape_image_urls(self, url: str) -> List[str]:
        """
        Extract all image URLs from a webpage
        
        Args:
            url: Website URL to scrape
        
        Returns:
            List of image URLs
        """
        logger.info(f"Scraping: {url}")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={config.USER_AGENT}")
        chrome_options.add_argument("--log-level=3")  # Suppress logs
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            
            # Wait for JavaScript to load images
            logger.info(f"Waiting {config.PAGE_LOAD_WAIT_SECONDS}s for page to load...")
            time.sleep(config.PAGE_LOAD_WAIT_SECONDS)
            
            # Scroll to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Extract image URLs
            img_elements = driver.find_elements(By.TAG_NAME, "img")
            source_elements = driver.find_elements(By.TAG_NAME, "source")
            
            urls = []
            
            # From <img> tags
            for img in img_elements:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                srcset = img.get_attribute("srcset")
                
                if src and src.startswith("http"):
                    urls.append(src)
                
                if srcset:
                    for candidate in srcset.split(','):
                        part = candidate.strip().split(' ')[0]
                        if part and part.startswith("http"):
                            urls.append(part)
            
            # From <source> tags
            for source in source_elements:
                src = source.get_attribute("src") or source.get_attribute("srcset")
                if src:
                    for candidate in src.split(','):
                        part = candidate.strip().split(' ')[0]
                        if part and part.startswith("http"):
                            urls.append(part)
            
            # Deduplicate and filter
            seen = set()
            result = []
            for u in urls:
                if u and u not in seen and not u.startswith('data:'):
                    seen.add(u)
                    result.append(u)
            
            logger.info(f"Found {len(result)} unique image URLs")
            return result
        
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return []
        
        finally:
            if driver:
                driver.quit()
    
    def download_image(self, image_url: str, page_url: str) -> Tuple[bytes, int, int]:
        """
        Download image to RAM
        
        Args:
            image_url: Image URL to download
            page_url: Page URL (for referer header)
        
        Returns:
            (image_bytes, width, height) or (None, None, None) on failure
        """
        headers = {
            "User-Agent": config.USER_AGENT,
            "Referer": page_url
        }
        
        try:
            response = requests.get(
                image_url,
                headers=headers,
                timeout=config.REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.debug(f"Failed to download {image_url}: HTTP {response.status_code}")
                return None, None, None
            
            image_bytes = response.content
            if not image_bytes:
                return None, None, None
            
            # Get image dimensions
            from PIL import Image
            import io
            try:
                img = Image.open(io.BytesIO(image_bytes))
                width, height = img.size
                return image_bytes, width, height
            except:
                return image_bytes, None, None
        
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout downloading {image_url}")
            return None, None, None
        except Exception as e:
            logger.debug(f"Error downloading {image_url}: {e}")
            return None, None, None


if __name__ == '__main__':
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    scraper = WebScraper(headless=True)
    
    test_url = "https://example.com"
    image_urls = scraper.scrape_image_urls(test_url)
    
    print(f"\nFound {len(image_urls)} images")
    for i, url in enumerate(image_urls[:5], 1):
        print(f"  {i}. {url}")
    
    if image_urls:
        print(f"\nTesting download of first image...")
        img_bytes, w, h = scraper.download_image(image_urls[0], test_url)
        if img_bytes:
            print(f"  Downloaded: {len(img_bytes)} bytes, {w}x{h} pixels")

import time
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import config
from models import JobListing

class LinkedInScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.current_category = ""

    def setup_driver(self):
        """Initializes the Selenium Chrome WebDriver."""
        print("Setting up WebDriver...")
        chrome_options = Options()
        
        # Use local profile
        if config.CHROME_PROFILE_PATH:
            chrome_options.add_argument(f"--user-data-dir={config.CHROME_PROFILE_PATH}")
            chrome_options.add_argument(f"--profile-directory={config.CHROME_PROFILE_DIR}")
        
        # Stability Flags - Crucial for Windows and avoiding crashes
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--remote-debugging-port=9222") # Helps with DevTools connection
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, config.PAGE_LOAD_WAIT)
        self.driver.maximize_window()

    def wait_for_login(self):
        """Simple check to wait for user to be logged in."""
        self.driver.get("https://www.linkedin.com/feed")
        
        # Check if we are on the login page or feed
        try:
            print("\n>>> CHECKING LOGIN STATUS...")
            # If the search bar or feed identity exists, we are logged in
            self.wait.until(EC.presence_of_element_located((By.ID, "global-nav-search")))
            print(">>> Logged in successfully!")
        except TimeoutException:
            print("\n====================================================")
            print("ACTION REQUIRED: You are not logged in.")
            print("Please log in manually in the Chrome window that just opened.")
            print("The script will wait for you to reach your LinkedIn Feed.")
            print("====================================================\n")
            
            # Keep waiting until the global search bar appears
            while True:
                try:
                    self.driver.find_element(By.ID, "global-nav-search")
                    print(">>> Detected login! Continuing...")
                    break
                except NoSuchElementException:
                    time.sleep(2)

    def search_jobs(self, query: str):
        """Navigates directly to LinkedIn search results using a 'Power URL'."""
        self.current_category = query
        print(f"\nSearching for '{query}'...")
        
        # Construct the URL with filters
        encoded_query = query.replace(" ", "%20")
        
        # Base URL: f_TPR=r86400 (Past 24 hours), f_E (Experience level)
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&f_TPR=r86400"
        
        if config.EXPERIENCE_FILTER:
            search_url += f"&f_E={config.EXPERIENCE_FILTER}"

        self.driver.get(search_url)
        time.sleep(config.ACTION_DELAY * 2)
        
        try:
            # Wait for either the search results list or the 'No results' message
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-search-results-list, .jobs-search-two-pane__container, .jobs-search-no-results-banner")))
            print(f"Results page loaded for {query}")
            
        except Exception as e:
            print(f"Error: Results page did not load for {query}")

    def extract_job_list(self, max_jobs: int) -> List[JobListing]:
        """Iterates through job cards on the left panel."""
        print("Extracting job list...")
        jobs = []
        
        try:
            # LinkedIn lazy loads job cards. We need to scroll the container.
            # Try to find the scrollable container for jobs
            scrollable_div = None
            scroll_selectors = [
                 (By.CSS_SELECTOR, ".jobs-search-results-list"),
                 (By.CLASS_NAME, "jobs-search-results-list"),
                 (By.CSS_SELECTOR, "div.jobs-search-results-list"),
                 (By.CSS_SELECTOR, "div.scaffold-layout__list-container")
            ]
            
            for by, val in scroll_selectors:
                try:
                    el = self.driver.find_element(by, val)
                    if el.is_displayed():
                        scrollable_div = el
                        break
                except:
                    continue

            if scrollable_div:
                print("Scrolling job list to load cards...")
                for _ in range(4): # Scroll several times
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                    time.sleep(1.5)
            else:
                print("Note: Could not find specific scrollable div, attempting general scroll.")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            # Now find the cards. Try multiple selectors.
            card_selectors = [
                "//li[contains(@class, 'jobs-search-results__list-item')]",
                "//div[contains(@class, 'job-card-container')]",
                "//li[contains(@data-occludable-job-id, '')]",
                "//a[contains(@class, 'job-card-list__title')]/ancestor::li"
            ]
            
            job_cards = []
            for selector in card_selectors:
                job_cards = self.driver.find_elements(By.XPATH, selector)
                if job_cards:
                    print(f"Found cards using selector: {selector}")
                    break
            
            if not job_cards:
                 print("Critical: No job cards found after scrolling. Are there results on this page?")
                 return []

            # HIDE MESSAGING OVERLAY (It often blocks clicks)
            try:
                self.driver.execute_script("document.querySelector('.msg-overlay-list-bubble')?.remove();")
                self.driver.execute_script("document.querySelector('#msg-overlay')?.remove();")
            except: pass

            max_search = min(len(job_cards), max_jobs * 2) # Look at more cards to account for duplicates
            print(f"Found {len(job_cards)} cards on page, extracting up to {max_jobs} unique jobs...")
            
            processed_id_set = set()
            
            for i in range(max_search):
                if len(jobs) >= max_jobs:
                    break
                    
                # Refetch cards
                current_cards = self.driver.find_elements(By.XPATH, selector)
                if i >= len(current_cards): break
                card = current_cards[i]
                
                try:
                    # Scroll card into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", card)
                    time.sleep(1.5)
                    
                    # CLICK using JavaScript (much more reliable for 'not interactable' errors)
                    # We try to find a link inside, otherwise click the card itself
                    try:
                        link = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title, a.job-card-container__link")
                        self.driver.execute_script("arguments[0].click();", link)
                    except:
                        self.driver.execute_script("arguments[0].click();", card)
                    
                    # Wait for right panel to change/load content
                    time.sleep(config.CARD_DELAY + 1)
                    
                    # Extract detailed data from the right panel
                    job_data = self.extract_job_details()
                    if job_data and job_data.title:
                        job_hash = f"{job_data.title}::{job_data.company}"
                        if job_hash not in processed_id_set:
                            processed_id_set.add(job_hash)
                            jobs.append(job_data)
                            print(f"[{len(jobs)}/{max_jobs}] Scraped: {job_data.title} at {job_data.company}")
                        else:
                            print(f"Skipping duplicate detection on index {i}: {job_data.title} at {job_data.company}")
                    else:
                        print(f"Attempt {i+1}: Could not extract details (Content didn't load or selectors failed).")
                        
                except Exception as e:
                    print(f"Failed to process card {i+1}: {e}")
                    
        except Exception as e:
            print(f"Detailed error in extract_job_list: {e}")
            
        return jobs

    def extract_job_details(self) -> JobListing:
        """Extracts data for the currently selected job from the right panel."""
        job = JobListing()
        job.category = self.current_category
        
        try:
            # 1. Identify the Right Panel Container
            detail_container = None
            container_selectors = [
                ".jobs-search-two-pane__details",
                ".scaffold-layout__detail",
                ".jobs-search__job-details",
                "section.job-view-layout"
            ]
            
            for sel in container_selectors:
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if el.is_displayed():
                        detail_container = el
                        break
                except: continue

            if not detail_container:
                detail_container = self.driver

            # 2. Wait for content to stabilize
            try:
                self.wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "h1, h2, .job-title").text.strip() != "")
            except:
                return None
            
            # 3. Extract Title
            title_selectors = [
                 (By.CSS_SELECTOR, "h1"), 
                 (By.CSS_SELECTOR, "h2.job-title"),
                 (By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__job-title"),
                 (By.CSS_SELECTOR, ".jobs-unified-top-card__job-title"),
                 (By.CSS_SELECTOR, ".job-view-layout h1")
            ]
            for by, sel in title_selectors:
                try:
                    text = detail_container.find_element(by, sel).text.strip()
                    if text:
                        job.title = text
                        break
                except: continue
                
            if not job.title: return None

            # 4. Extract Company
            company_selectors = [
                 (By.CSS_SELECTOR, ".jobs-unified-top-card__company-name"),
                 (By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__company-name"),
                 (By.CSS_SELECTOR, ".jobs-unified-top-card__primary-description a")
            ]
            for by, sel in company_selectors:
                try:
                    text = detail_container.find_element(by, sel).text.strip()
                    if text:
                        job.company = text
                        break
                except: continue
                
            # 5. Extract Location & Time
            try:
                meta_selectors = [
                    ".job-details-jobs-unified-top-card__primary-description",
                    ".jobs-unified-top-card__primary-description",
                    ".job-details-jobs-unified-top-card__company-info"
                ]
                
                meta_text = ""
                for ms in meta_selectors:
                    try:
                        meta_text = detail_container.find_element(By.CSS_SELECTOR, ms).text
                        if meta_text: break
                    except: continue

                if meta_text:
                    parts = [p.strip() for p in meta_text.split("·") if p.strip()]
                    if len(parts) >= 1:
                        time_index = -1
                        for idx, p in enumerate(parts):
                            if any(word in p.lower() for word in ["ago", "hours", "days", "weeks", "month"]):
                                time_index = idx
                                break
                        
                        if time_index != -1:
                            job.posted_time = parts[time_index]
                            if time_index > 0:
                                prev = parts[time_index - 1]
                                if job.company and job.company.lower() in prev.lower():
                                    pass
                                else:
                                    job.location = prev
                        
                        if not job.location and len(parts) >= 2:
                            if job.company and job.company.lower() in parts[0].lower():
                                job.location = parts[1]
                            else:
                                job.location = parts[0]
            except: pass
                
            # 6. Extract Description & Scan Skills
            desc_selectors = [
                (By.CSS_SELECTOR, "#job-details"),
                (By.CSS_SELECTOR, ".jobs-description__content"),
                (By.CSS_SELECTOR, ".jobs-box__html-content")
            ]
            for by, sel in desc_selectors:
                try:
                    text = detail_container.find_element(by, sel).text.strip()
                    if text:
                        job.description = text
                        break
                except: continue

            job.clean()
            return job
            
        except Exception:
             return None


    def close(self):
        """Closes the browser session."""
        if self.driver:
             print("Closing browser...")
             self.driver.quit()

import time
import os
import re
from datetime import datetime, timedelta
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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
        self.global_processed_ids = set() # Persistent across multiple search queries

    def _calculate_absolute_time(self, relative_str: str, base_time: datetime) -> datetime:
        """
        Converts strings like '17 hours ago', '2 days ago', '3w', '1mo' into absolute datetimes.
        """
        if not relative_str or not isinstance(relative_str, str):
            return base_time
            
        r_lower = relative_str.lower().strip()
        
        # 1. Handle "Just now"
        if "now" in r_lower:
            return base_time
            
        # 2. Pattern Matching for "X [unit] ago"
        match = re.search(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", r_lower)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            if unit == "minute": return base_time - timedelta(minutes=value)
            if unit == "hour":   return base_time - timedelta(hours=value)
            if unit == "day":    return base_time - timedelta(days=value)
            if unit == "week":   return base_time - timedelta(weeks=value)
            if unit == "month":  return base_time - timedelta(days=value * 30)
            if unit == "year":   return base_time - timedelta(days=value * 365)

        # 3. Pattern Matching for Abbreviations (e.g. "3h", "2d", "1w", "1mo")
        match_abbr = re.search(r"(\d+)(m|h|d|w|mo|y)", r_lower)
        if match_abbr:
            value = int(match_abbr.group(1))
            unit = match_abbr.group(2)
            
            if unit == "m":  return base_time - timedelta(minutes=value)
            if unit == "h":  return base_time - timedelta(hours=value)
            if unit == "d":  return base_time - timedelta(days=value)
            if unit == "w":  return base_time - timedelta(weeks=value)
            if unit == "mo": return base_time - timedelta(days=value * 30)
            if unit == "y":  return base_time - timedelta(days=value * 365)
            
        return base_time

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

    def extract_job_list(self, max_jobs: int, job_queue=None) -> List[JobListing]:
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

            current_index = 0
            while len(jobs) < max_jobs:
                # 1. Refetch cards to account for dynamic loading/infinite scroll
                current_cards = self.driver.find_elements(By.XPATH, selector)
                
                # If we've exhausted all visible cards, we can't do more
                if current_index >= len(current_cards):
                    print(f"Reached end of visible cards ({len(current_cards)} found).")
                    break
                
                card = current_cards[current_index]
                current_index += 1 # Advance for next iteration
                
                try:
                    # Scroll card into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", card)
                    time.sleep(1.0)
                    
                    # CLICK using JavaScript
                    try:
                        link = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title, a.job-card-container__link")
                        self.driver.execute_script("arguments[0].click();", link)
                    except:
                        self.driver.execute_script("arguments[0].click();", card)
                    
                    # Wait for right panel content to update
                    time.sleep(config.CARD_DELAY + 1)
                    
                    # Extract detailed data from the right panel
                    job_data = self.extract_job_details()
                    if job_data and job_data.title:
                        # Uniqueness check: Primary check = Apply Link (Job ID), Fallback = Title + Company
                        job_key = job_data.apply_link if job_data.apply_link else f"{job_data.title.lower()}::{job_data.company.lower()}"
                        
                        if job_key not in self.global_processed_ids:
                            self.global_processed_ids.add(job_key)
                            jobs.append(job_data)
                            print(f"[{len(jobs)}/{max_jobs}] Scraped: {job_data.title} at {job_data.company}")
                            
                            if job_queue:
                                job_queue.put(job_data)
                        else:
                            # Standard LinkedIn behavior: it often repeats cards across searches
                            print(f"Skipping duplicate job: {job_data.title} at {job_data.company}")
                            pass 
                    else:
                        print(f"Card {current_index}: Content didn't load, skipping.")
                        
                except Exception as e:
                    print(f"Error processing card {current_index}: {e}")
                    
        except Exception as e:
            print(f"Detailed error in extract_job_list: {e}")
            
        return jobs

    def extract_job_details(self) -> JobListing:
        """Extracts data for the currently selected job from the right panel."""
        job = JobListing()
        job.category = self.current_category
        job.scraped_at = datetime.now().isoformat()
        
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
                # 5a. Broad search for "Posted Time"
                time_keywords = ["ago", "hours", "hrs", "minute", "day", "week", "month", "year", "1h", "2h", "3h"]
                time_xpath = ".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ago') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'hour')]"
                
                try:
                    time_els = detail_container.find_elements(By.XPATH, time_xpath)
                    for te in time_els:
                        t_text = te.text.strip().replace("·", "")
                        if any(k in t_text.lower() for k in time_keywords) and len(t_text) < 30:
                            job.posted_time = t_text
                            break
                except: pass

                # 5b. Robust absolute date calculation
                if job.posted_time:
                    job.posted_time = job.posted_time.replace("·", "").replace("•", "").strip()
                    try:
                        base_dt = datetime.fromisoformat(job.scraped_at)
                        absolute_dt = self._calculate_absolute_time(job.posted_time, base_dt)
                        job.posted_at = absolute_dt.strftime("%Y-%m-%d %H:%M")
                    except: pass
                
            except Exception:
                pass

            # 6. Extract Description
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
                except:
                    continue
                
            # 7. Extract Apply Link
            try:
                # 7a. Get the LinkedIn Job URL (fallback/primary)
                current_url = self.driver.current_url
                job_id_match = re.search(r"currentJobId=(\d+)", current_url)
                
                if job_id_match:
                    job_id = job_id_match.group(1)
                    job.apply_link = f"https://www.linkedin.com/jobs/view/{job_id}/"
                elif "/jobs/view/" in current_url:
                    job.apply_link = current_url.split("?")[0]

                # Check the apply button text/behavior
                apply_selectors = [
                    ".jobs-apply-button--top-card button",
                    ".jobs-apply-button",
                    "button[aria-label*='Apply']",
                    "a[aria-label*='Apply']"
                ]
                
                for sel in apply_selectors:
                    try:
                        btn = detail_container.find_element(By.CSS_SELECTOR, sel)
                        btn_text = btn.text.strip().lower()
                        
                        if "easy apply" in btn_text:
                            # Already handled by current_url above
                            break
                        elif "apply" in btn_text:
                            # Check if it's a direct link
                            href = btn.get_attribute("href")
                            if href:
                                job.apply_link = href
                                break
                            # Some external buttons are just buttons that redirect
                            # We keep the LinkedIn link as a fallback
                            break
                    except: continue
            except Exception:
                pass

            job.clean()
            return job
            
        except Exception:
             return None


    def close(self):
        """Closes the browser session."""
        if self.driver:
             print("Closing browser...")
             self.driver.quit()

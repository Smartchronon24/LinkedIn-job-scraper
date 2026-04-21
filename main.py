from scraper_controller import LinkedInScraper
from views import JobView
import config

def main():
    print("=== LinkedIn Job Scraper ===")
    
    # 1. Setup Controller
    scraper = LinkedInScraper()
    
    try:
        # Initialize browser
        scraper.setup_driver()
        
        # New: Ensure user is logged in
        scraper.wait_for_login()
        
        # 2. Perform Batch Search Flow
        all_jobs = []
        for role in config.SEARCH_QUERIES:
            try:
                scraper.search_jobs(role)
                category_jobs = scraper.extract_job_list(config.MAX_JOBS)
                all_jobs.extend(category_jobs)
                print(f"--- Collected {len(category_jobs)} jobs for {role} ---")
            except Exception as e:
                print(f"Error during search for '{role}': {e}")
        
        # Display summary in console
        print("\n=== Batch Scraping Results ===")
        print(f"Total jobs collected: {len(all_jobs)}")
        for idx, job in enumerate(all_jobs, 1):
            JobView.print_job_summary(job, idx)
            
        # 3. Save Output (via View)
        JobView.save_to_csv(all_jobs, config.OUTPUT_FILE)
        
    except Exception as e:
        print(f"\nAn error occurred during execution: {e}")
        
    finally:
        # Ensure browser is always closed
        scraper.close()
        print("\nAll done!")

if __name__ == "__main__":
    main()

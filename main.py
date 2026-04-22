import json
import config
from scraper_controller import LinkedInScraper
from views import JobView
from llm_processor import OllamaProcessor

def main():
    print("=== LinkedIn Job Scraper ===")
    
    # 1. Setup Controller
    scraper = LinkedInScraper()
    
    try:
        # Initialize browser
        scraper.setup_driver()
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
        
        if not all_jobs:
            print("No jobs were collected. Skipping processing.")
            return

        # Display summary in console
        print("\n=== Batch Scraping Results ===")
        for idx, job in enumerate(all_jobs, 1):
            JobView.print_job_summary(job, idx)
            
        # 3. LLM Insights (Ollama)
        final_data = []
        if config.OLLAMA_ENABLED:
            print("\n=== Generating Insights (Local Llama3) ===")
            processor = OllamaProcessor()
            
            for idx, job in enumerate(all_jobs, 1):
                print(f"[{idx}/{len(all_jobs)}] Processing: {job.title} at {job.company}...")
                insights = processor.process_description(job.description)
                
                if not insights:
                    insights = {
                        "primary_skills": [], "secondary_skills": [], 
                        "coding_skills": {"languages": []},
                        "experience": {"range": [None], "description": ""},
                        "responsibilities": []
                    }

                # Enrich with job Metadata for CSV mapping
                insights["job_metadata"] = {
                    "category": job.category,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "posted_at": job.posted_at,
                    "scraped_at": job.scraped_at,
                    "description": job.description
                }
                final_data.append(insights)
            
            # Save Insights to JSON (Verification Log)
            with open(config.OLLAMA_INSIGHTS_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2)
            
        # 4. Save Enriched Data to CSV
        JobView.save_to_csv(final_data if final_data else all_jobs, config.OUTPUT_FILE)
            
    except Exception as e:
        print(f"\nAn error occurred during execution: {e}")
    finally:
        scraper.close()
        print("\nAll done!")

if __name__ == "__main__":
    main()

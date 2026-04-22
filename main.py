import json
import config
import threading
import queue
from scraper_controller import LinkedInScraper
from views import JobView
from llm_processor import OllamaProcessor

def llm_worker(job_queue, final_data, data_lock):
    """
    Background worker that processes jobs from the queue as they arrive.
    This runs in a separate thread so the scraper can keep working.
    """
    try:
        processor = OllamaProcessor()
        
        while True:
            # Get a job from the queue
            job = job_queue.get()
            
            # 'None' is our 'Poison Pill' to stop the thread
            if job is None:
                job_queue.task_done()
                break
                
            print(f"\n[AI Worker] Processing: {job.title} at {job.company}...")
            
            try:
                # Prepare context for LLM
                content_to_process = f"""Role: {job.title}
Company: {job.company}
Scraped Location: {job.location}
Apply Link: {job.apply_link}

Job Description:
{job.description}"""
                insights = processor.process_description(content_to_process)
                
                # Fallback if LLM fails
                if not insights:
                    insights = {
                        "skills": {
                            "primary_skills": [], "secondary_skills": [], 
                            "soft_skills": [], "coding_skills": {"languages": []}
                        },
                        "experience": {"range": [None], "description": ""},
                        "responsibilities": [],
                        "location_insights": {"city": "", "state": "", "country": "", "work_model": "Unknown"},
                        "apply_link": ""
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
                
                # Use a lock to safely append to the shared list
                with data_lock:
                    final_data.append(insights)
                    
            except Exception as e:
                print(f"Error in AI worker for {job.title}: {e}")
                
            # Signal that the processing for this specific item is done
            job_queue.task_done()
    except Exception as init_err:
        print(f"Worker initialization failed: {init_err}")

def main():
    print("=== LinkedIn Job Scraper (Parallel Mode) ===")
    
    # 1. Setup inter-thread communication
    job_queue = queue.Queue()
    final_data = [] # Shared list for processed results
    data_lock = threading.Lock() # Protects the shared list
    
    scraper = LinkedInScraper()
    
    try:
        # 2. Start the AI Background Thread(s)
        worker_threads = []
        if config.OLLAMA_ENABLED:
            for _ in range(config.OLLAMA_MAX_WORKERS):
                t = threading.Thread(
                    target=llm_worker, 
                    args=(job_queue, final_data, data_lock),
                    daemon=True
                )
                t.start()
                worker_threads.append(t)
            print(f"Started {len(worker_threads)} background AI worker(s).")
        
        # 3. Setup Browser
        scraper.setup_driver()
        scraper.wait_for_login()
        
        # 4. Perform Scraping
        # We pass the job_queue into the scraper so it can pipe data in real-time
        for role in config.SEARCH_QUERIES:
            try:
                scraper.search_jobs(role)
                scraper.extract_job_list(config.MAX_JOBS, job_queue=job_queue)
            except Exception as e:
                print(f"Error during search for '{role}': {e}")
        
        # 5. Shutdown Browser Early
        scraper.close()
        print("\nScraping complete, browser closed.")

        # 6. Wait for AI to finish
        if config.OLLAMA_ENABLED:
            print(f"Waiting for {len(worker_threads)} background AI worker(s) to finish...")
            
            # Send one poison pill (None) for EACH worker thread
            for _ in range(len(worker_threads)):
                job_queue.put(None) 
            
            # Wait for all worker threads to finish
            for t in worker_threads:
                t.join() 
            
            # Save Insights to JSON (Verification Log)
            with open(config.OLLAMA_INSIGHTS_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2)
            
        # 7. Save final dataset to CSV
        JobView.save_to_csv(final_data if final_data else [], config.OUTPUT_FILE)
            
    except Exception as e:
        print(f"\nAn error occurred during execution: {e}")
    finally:
        # Final cleanup for consistency
        if scraper.driver:
            scraper.close()
        print("\nAll done!")

if __name__ == "__main__":
    main()

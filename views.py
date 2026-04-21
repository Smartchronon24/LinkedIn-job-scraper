import csv
import os
from typing import List
from models import JobListing
import config

class JobView:
    @staticmethod
    def print_job_summary(job: JobListing, index: int):
        """Prints a brief summary to the console."""
        print(f"[{index}] {job.title} at {job.company} ({job.location}) - {job.posted_time}")

    @staticmethod
    def save_to_csv(jobs: List[JobListing], filepath: str):
        """Exports the list of jobs to a CSV file."""
        if not jobs:
            print("No jobs to save.")
            return
            
        print(f"\nSaving {len(jobs)} jobs to: {filepath}...")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        fieldnames = ["Category", "Title", "Company", "Location", "Posted Time", "Description"]
        
        # Determine mode: write header only if not appending or if file is new
        file_exists = os.path.isfile(filepath)
        mode = "a" if (config.APPEND_TO_EXISTING and file_exists) else "w"
        
        with open(filepath, mode=mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header if we are starting a new file
            if mode == "w":
                writer.writeheader()
            
            for job in jobs:
                writer.writerow({
                    "Category": job.category,
                    "Title": job.title,
                    "Company": job.company,
                    "Location": job.location,
                    "Posted Time": job.posted_time,
                    "Description": job.description
                })
                
        print("Save complete!")

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
    def save_to_csv(enriched_jobs: List[dict], filepath: str):
        """Exports the list of enriched job data to a CSV file."""
        if not enriched_jobs:
            print("No data to save.")
            return
            
        print(f"\nSaving {len(enriched_jobs)} enriched jobs to: {filepath}...")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        fieldnames = config.CSV_HEADERS
        
        # Determine mode: write header only if not appending or if file is new
        file_exists = os.path.isfile(filepath)
        mode = "a" if (config.APPEND_TO_EXISTING and file_exists) else "w"
        
        with open(filepath, mode=mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if mode == "w":
                writer.writeheader()
            
            for item in enriched_jobs:
                # Map JSON/Metadata fields to CSV columns
                meta = item.get("job_metadata", {})
                exp  = item.get("experience", {})
                coding = item.get("coding_skills", {})
                
                # Format lists as semicolon-separated strings
                writer.writerow({
                    "Category": meta.get("category"),
                    "Title": meta.get("title"),
                    "Company": meta.get("company"),
                    "Location": meta.get("location"),
                    "Primary Skills": "; ".join(item.get("primary_skills", [])),
                    "Secondary Skills": "; ".join(item.get("secondary_skills", [])),
                    "Languages": "; ".join(coding.get("languages", [])),
                    "Min Exp": exp.get("range", [None])[0] if isinstance(exp.get("range"), list) else None,
                    "Max Exp": exp.get("range", [None])[-1] if isinstance(exp.get("range"), list) and len(exp.get("range")) > 1 else (exp.get("range", [None])[0] if isinstance(exp.get("range"), list) else None),
                    "Responsibilities": " | ".join(item.get("responsibilities", [])),
                    "Experience Summary": exp.get("description"),
                    "Posted At": meta.get("posted_at"),
                    "Scraped At": meta.get("scraped_at"),
                    "Description": meta.get("description")
                })
                
        print("Save complete!")

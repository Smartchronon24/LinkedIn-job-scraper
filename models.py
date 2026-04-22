from dataclasses import dataclass

@dataclass
class JobListing:
    title: str = ""
    company: str = ""
    location: str = ""
    posted_time: str = ""    # Raw string from LinkedIn (e.g. "17 hours ago")
    description: str = ""
    category: str = ""       # The role searched (e.g. Data Engineer)
    scraped_at: str = ""     # ISO timestamp of when the job was scraped
    posted_at: str = ""      # Calculated absolute timestamp (Silver layer)
    apply_link: str = ""     # URL for the job application
    
    def clean(self):
        """Basic text normalization."""
        self.title = self.title.strip()
        self.company = self.company.strip()
        self.location = self.location.strip()
        self.posted_time = self.posted_time.strip()
        self.category = self.category.strip()
        self.scraped_at = self.scraped_at.strip()
        self.posted_at = self.posted_at.strip()
        self.apply_link = self.apply_link.strip()
        
        # Simple whitespace replacement for description
        if self.description:
            lines = [line.strip() for line in self.description.splitlines() if line.strip()]
            self.description = "\n".join(lines).strip()

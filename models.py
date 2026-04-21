from dataclasses import dataclass

@dataclass
class JobListing:
    title: str = ""
    company: str = ""
    location: str = ""
    posted_time: str = ""
    description: str = ""
    category: str = ""   # The role searched (e.g. Data Engineer)
    
    def clean(self):
        """Basic text normalization."""
        self.title = self.title.strip()
        self.company = self.company.strip()
        self.location = self.location.strip()
        self.posted_time = self.posted_time.strip()
        self.category = self.category.strip()
        
        # Simple whitespace replacement for description
        if self.description:
            lines = [line.strip() for line in self.description.splitlines() if line.strip()]
            self.description = "\n".join(lines).strip()

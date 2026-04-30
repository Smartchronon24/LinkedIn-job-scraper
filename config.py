# =============================================================================
# config.py — Central Configuration
# =============================================================================
# Adjust these settings before running the scraper.

import os

# ---------------------------------------------------------------------------
# Chrome Profile (keeps you logged in — no password needed)
# ---------------------------------------------------------------------------
# Find your Chrome profile path:
#   Windows: C:\Users\<YourName>\AppData\Local\Google\Chrome\User Data
#   macOS  : ~/Library/Application Support/Google/Chrome
#   Linux  : ~/.config/google-chrome
#
# Leave CHROME_PROFILE_PATH as None to open a plain browser window instead.

# 1. Use a local folder in THIS project for the browser data.
# This prevents it from clashing with your regular Chrome.
CHROME_PROFILE_PATH = os.path.join(os.getcwd(), "chrome_data")

# 2. Default profile folder inside our data dir.
CHROME_PROFILE_DIR = "Default"


# ---------------------------------------------------------------------------
# Search Parameters (Batch Mode)
# ---------------------------------------------------------------------------
# Add multiple roles here to scrape them all in one go
SEARCH_QUERIES = ["Data Engineer/Scientist", "Python Developer", "AI Developer"] 
MAX_JOBS       = 5                 # Per category

# ---------------------------------------------------------------------------
# Filter Parameters
# ---------------------------------------------------------------------------
# Values: 1=Intern, 2=Entry, 3=Associate, 4=Mid-Sr, 5=Director, 6=Exec
# Example: "2,3" for Entry and Associate level. Leave as "" for no filter.
EXPERIENCE_FILTER = "2" #,1,3,4,5,6" 

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
OUTPUT_DIR          = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE         = os.path.join(OUTPUT_DIR, "linkedin_jobs.csv")
APPEND_TO_EXISTING  = False        # Set to True to keep old results in the CSV

# Standard format for both Bronze and Silver
CSV_HEADERS = [
    "Category", "Title", "Company", "Location", 
    "Primary Skills", "Secondary Skills", "Soft Skills", "Languages",
    "Apply Link", "Min Exp", "Max Exp", "Responsibilities", "Experience Summary",
    "Posted At", "Scraped At", "Description"
]

# ---------------------------------------------------------------------------
# Timing (seconds) — tweak if LinkedIn loads slowly on your connection
# ---------------------------------------------------------------------------
PAGE_LOAD_WAIT       = 10   # Max wait for elements (WebDriverWait timeout)
ACTION_DELAY         = 2    # Pause between major actions
CARD_DELAY           = 1.5  # Pause after clicking each job card

# ---------------------------------------------------------------------------
# Ollama / LLM Configuration
# ---------------------------------------------------------------------------
OLLAMA_MODEL         = "llama3"
OLLAMA_URL           = "http://localhost:11434/api/generate"
OLLAMA_INSIGHTS_FILE = "Webscraping/job_insights.json"
OLLAMA_ENABLED       = True        # Set to False to skip LLM processing
OLLAMA_MAX_WORKERS   = 1           # Number of parallel AI threads (1 is best for local)

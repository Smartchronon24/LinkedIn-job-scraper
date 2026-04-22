import requests
import json
import re
from config import OLLAMA_MODEL, OLLAMA_URL

class OllamaProcessor:
    """Handles communication with the local Ollama instance for job insight extraction."""

    def __init__(self):
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self):
        """Builds the system prompt based on the granular skills re-engineering."""
        return """
You are a strict information extraction system.
Extract structured data from the job description and return ONLY valid JSON.
DO NOT include explanations, comments, or extra text.

Output Schema:
{
  "skills": {
    "primary_skills": [],   // MANDATORY technical skills + all coding languages
    "secondary_skills": [], // PREFERRED/DESIRED technical skills only
    "soft_skills": [],      // Soft skills (e.g., communication, problem solving)
    "coding_skills": {
      "type": "any_one | all_required | unspecified",
      "languages": []       // Split by slashes: C/C++ -> ["C", "C++"]
    }
  },
  "experience": {
    "description": "string",
    "range": [min, max] or [exact] or null
  },
  "responsibilities": [],
  "apply_link": "string",
  "location_insights": {
    "city": "string",
    "state": "string",
    "country": "string",
    "work_model": "Remote | Hybrid | On-site | Unknown"
  }
}

Rules:
1. PRIMARY SKILLS:
- Extract technical skills listed under 'Requirements', 'Qualifications', or 'What you will need'.
- MUST include all languages found in 'coding_skills'.
- EXCLUDE vague terms (e.g., "Technology", "Systems").

2. SECONDARY SKILLS:
- Extract technical skills listed as 'Preferred', 'Plus', 'Nice to have', or 'Desired'.
- Do NOT include soft skills here.

3. SOFT SKILLS:
- Extract interpersonal and character-based skills (e.g., "Communication", "Teamwork", "Problem Solving").
- Keep items concise but descriptive (e.g., "Exceptional communication").

4. CODING SKILLS:
- Extract programming languages separately.
- Split combined strings: "C/C++/Java" must be ["C", "C++", "Java"].

5. EXPERIENCE:
- Clean readable sentence for the description.
- RANGE: [4, 7] for "4-7 years". Freshers/Interns = [0].
more examples: "4-7" or "4 to 7" years of experience should be represented as: [4, 7]
if "no work experience needed" or "freshers" or "Intern" or related values, then: [0]
DONOT by any chance return value like [x, null] or [null, x] where x stands for any positive numeric value.  

6. GENERAL:
- Remove duplicates across all categories.
- Normalize capitalization (e.g., "python" -> "Python").

7. LOCATION:
- Extract City, State, Country from the context provided (use Scraped Location as a hint).
- Work model: Identify if the role is Remote, Hybrid, or On-site. Prioritize the description over the location hint if it says "Remote". Fallback to 'Unknown'.
"""

    def process_description(self, description):
        """Sends the description to Ollama and returns the parsed JSON insights."""
        full_prompt = f"{self.system_prompt}\n\nJob Description:\n{description}\n"
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "format": "json" # Ollama supports forcing JSON mode
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=300)
            response.raise_for_status()
            
            result = response.json()
            raw_text = result.get("response", "")
            
            if not raw_text.strip():
                return None
                
            return self._parse_json(raw_text)
        except Exception as e:
            print(f"ERROR: Ollama processing failed: {e}")
            return None

    def _parse_json(self, text):
        """Cleans and parses the LLM response into a dictionary."""
        try:
            # Try direct parse
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: find the first { and last }
            try:
                match = re.search(r'(\{.*\})', text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            except:
                pass
            return None

if __name__ == "__main__":
    # Quick internal test
    processor = OllamaProcessor()
    test_desc = "Looking for a Python developer with 3-5 years exp in Django. Excellent team player."
    print("Testing Ollama Processor...")
    res = processor.process_description(test_desc)
    print(json.dumps(res, indent=2))

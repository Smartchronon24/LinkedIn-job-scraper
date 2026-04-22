import requests
import json
import re
from config import OLLAMA_MODEL, OLLAMA_URL

class OllamaProcessor:
    """Handles communication with the local Ollama instance for job insight extraction."""

    def __init__(self):
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self):
        """Builds the system prompt based on the full rules in scratchpad.txt."""
        return """
You are a strict information extraction system.
Extract structured data from the job description and return ONLY valid JSON.
DO NOT include explanations, comments, or extra text.

Output Schema:
{
  "primary_skills": [],
  "secondary_skills": [],
  "coding_skills": {
    "type": "any_one | all_required | unspecified",
    "languages": []
  },
  "experience": {
    "description": "string",
    "range": [min, max] or [exact] or null
  },
  "responsibilities": []
}

Rules:
1. PRIMARY SKILLS:
- Include ONLY technical, domain-relevant skills (e.g. Data Structures, Algorithms, OOP)
- EXCLUDE vague terms like "Design", "Technology", "Systems"

2. SECONDARY SKILLS:
- Include soft skills only (e.g. communication, problem solving, teamwork)

3. CODING SKILLS:
- Extract programming languages separately. 
- IMPORTANT: Split combined strings! "C/C++/Java" must be ["C", "C++", "Java"]
- If job says "any one of X/Y/Z": type = "any_one", languages = ["X", "Y", "Z"]
- If job requires all: type = "all_required"
- If unclear: type = "unspecified"

4. EXPERIENCE:
- Keep description as a clean readable sentence without unrelated text.
- RANGE: Extract NUMERIC values (e.g. [4, 7] for "4-7 years"). 
- Freshers/Interns/No experience needed: [0]
- DONOT return [x, null] or [null, x]. If one number, use [x] or [x, x].
- If not present: null

5. RESPONSIBILITIES:
- Extract actual duties. Keep each item concise.

6. GENERAL:
- Remove duplicates, normalize capitalization, keep output clean and minimal.
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
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            raw_text = result.get("response", "")
            
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
            print(f"DEBUG: Failed to parse LLM JSON: {text[:100]}...")
            return None

if __name__ == "__main__":
    # Quick internal test
    processor = OllamaProcessor()
    test_desc = "Looking for a Python developer with 3-5 years exp in Django. Excellent team player."
    print("Testing Ollama Processor...")
    res = processor.process_description(test_desc)
    print(json.dumps(res, indent=2))

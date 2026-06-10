import json
import os
from src.llm_client import get_llm_client

class ProfileParser:
    def __init__(self, api_key=None):
        self.llm_client = get_llm_client(api_key)


    def parse_profile(self, profile_data: dict) -> dict:
        """
        Parses the student profile using GPT-4.1 to extract search constraints,
        keywords, and academic strength for tiering.
        """
        prompt = f"""
You are an expert academic mentor helping international students find PhD supervisors.
Analyze the following student profile JSON and extract key search criteria for identifying potential supervisors:

Student Profile:
{json.dumps(profile_data, indent=2)}

Please return a JSON object with the following fields:
1. "target_countries": A list of ISO 2-letter country codes (e.g., "US", "CA", "GB") extracted from the target countries constraint.
2. "research_interests": A list of 3-5 high-level research interest areas stated by the student.
3. "search_keywords": A list of 4-8 precise, technical keywords/phrases to search for recent publications on OpenAlex (e.g., "deep reinforcement learning", "quadrotor control", "medical image segmentation"). These should be highly specific to avoid keyword overlap errors.
4. "academic_tier_level": One of "elite" (e.g., B.Tech from top university with high GPA and publications), "strong" (e.g., good GPA, solid projects/theses, maybe minor publications), or "standard" (average GPA, less research experience). This will be used to calibrate Reach/Target/Safety rankings.
5. "academic_strength_summary": A 2-sentence summary explaining why you assigned that academic tier level based on their grades, publication venues, and university prestige.

Your output must be a valid JSON object. Do not include any markdown formatting or extra text outside the JSON.
"""

        try:
            return self.llm_client.call_llm_json(
                prompt=prompt,
                system_message="You are a helpful assistant that returns only valid JSON.",
                temperature=0.1
            )
        except Exception as e:
            print(f"Error parsing profile with LLM: {e}")
            # Fallback values in case of failure
            return {
                "target_countries": profile_data.get("target_countries", ["US"]),
                "research_interests": profile_data.get("research_interests", []),
                "search_keywords": profile_data.get("research_interests", []),
                "academic_tier_level": "strong",
                "academic_strength_summary": "Fallback profile extraction due to API error."
            }

if __name__ == "__main__":
    # Test script
    import sys
    test_profile_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_profile.json")
    if os.path.exists(test_profile_path):
        with open(test_profile_path, "r") as f:
            profile = json.load(f)
        parser = ProfileParser()
        parsed = parser.parse_profile(profile)
        print("Parsed Profile Output:")
        print(json.dumps(parsed, indent=2))
    else:
        print(f"Test profile not found at {test_profile_path}")

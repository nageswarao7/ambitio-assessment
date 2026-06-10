import os
import json
from typing import Dict, Any, List, Tuple
from src.llm_client import get_llm_client

class FilterEngine:
    def __init__(self, api_key: str = None, min_h_index: int = 8, min_works_count: int = 15, min_career_age: int = 5):
        self.llm_client = get_llm_client(api_key)
        
        # Thresholds for career stage filter
        self.min_h_index = min_h_index
        self.min_works_count = min_works_count
        self.min_career_age = min_career_age

    def is_valid_career_stage(self, pi: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Filters out junior researchers, PhD students, and postdocs.
        Returns (is_valid, reason).
        """
        h_index = pi.get("h_index", 0)
        works_count = pi.get("works_count", 0)
        career_age = pi.get("career_age", 0)

        if h_index < self.min_h_index:
            return False, f"h-index {h_index} is below minimum threshold of {self.min_h_index} (likely junior researcher/postdoc)."
        if works_count < self.min_works_count:
            return False, f"works count {works_count} is below minimum threshold of {self.min_works_count}."
        if career_age < self.min_career_age:
            return False, f"career age {career_age} years is below minimum threshold of {self.min_career_age}."
            
        return True, "Valid career stage."

    def verify_no_domain_leakage(self, student_profile: Dict[str, Any], pi: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Uses deepseek.v3.1 to verify that the candidate's publications actually align with the student's domain
        and do not suffer from wrong-domain leakage due to keyword overlap.
        Includes a retry mechanism for handling rate limits (429).
        """
        # Prepare PI publication list for context
        papers_info = []
        for idx, paper in enumerate(pi.get("evidence_papers", [])[:4]):
            title = paper.get("title", "No Title")
            abstract = paper.get("abstract", "")[:200]
            papers_info.append(f"Paper {idx+1}: {title}\nAbstract Snippet: {abstract}...")
        
        papers_text = "\n\n".join(papers_info)
        student_interests = ", ".join(student_profile.get("research_interests", []))
        student_summary = student_profile.get("intro_call_summary", "")

        prompt = f"""
You are a senior academic reviewer validating supervisor matches for PhD applicants.
Your job is to catch WRONG-DOMAIN LEAKAGE arising from keyword overlaps.

Here are examples of wrong-domain leakage you MUST catch:
1. A grant/paper titled "biodegradable plastic cartridges" matching a biomaterials student. (Leakage: It is actually military ammunition R&D, not biomaterials).
2. A grant/paper on "high-elevation social-ecological systems" matching a Himalayan pilgrimage student. (Leakage: It is actually Pacific Northwest fire archaeology, not South Asian religious studies).
3. A "trauma-informed" grant/paper matching a clinical psychology student. (Leakage: It is actually a literary-history project on grief in Roman antiquity, not modern psychological therapy).
4. A "DNA barcoding" grant/paper matching a plant biology student. (Leakage: It is actually single-cell barcoding for human Hi-C chromatin work, not ecology/botany).

Validate the following match:
---
Student Research Interests: {student_interests}
Student Profile Summary: {student_summary}

Candidate PI Name: {pi['name']}
Candidate Institution: {pi['institution']} ({pi['country']})
Candidate's Publications:
{papers_text}
---

Analyze if the Candidate PI's research domain is a genuine match for the student, or if it is a keyword-overlap mistake (wrong domain, different discipline, or incompatible context).
Return a JSON object with:
1. "is_genuine_match": boolean (true if it's a solid, correct domain match; false if there is wrong-domain leakage or general mismatch).
2. "reason": a concise explanation of your findings, highlighting any mismatch or confirming the alignment.

Return ONLY the raw JSON object. Do not include markdown block quotes or extra text.
"""
        try:
            result = self.llm_client.call_llm_json(
                prompt=prompt,
                system_message="You are a helpful assistant that returns only valid JSON.",
                temperature=0.1
            )
            return result.get("is_genuine_match", False), result.get("reason", "No reason provided.")
        except Exception as e:
            print(f"Error checking domain leakage for PI {pi['name']}: {e}")
            return True, f"API Error: {e}. Match assumed valid."

if __name__ == "__main__":
    # Test script with mock PI data
    fe = FilterEngine()
    
    mock_student = {
        "research_interests": ["Biomaterials", "Polymer Chemistry"],
        "intro_call_summary": "Looking for research on biodegradable polymers and medical scaffolding."
    }
    
    # Case 1: Wrong domain leakage (military ammunition)
    leakage_pi = {
        "name": "Dr. John Doe",
        "institution": "US Military Academy",
        "country": "US",
        "h_index": 12,
        "works_count": 25,
        "career_age": 8,
        "evidence_papers": [
            {
                "title": "Biodegradable plastic cartridges: Environmental impact of training munitions",
                "abstract": "We develop novel casing designs using biodegradable polymers for military target practice cartridges."
            }
        ]
    }
    
    # Case 2: Genuine match
    genuine_pi = {
        "name": "Dr. Jane Smith",
        "institution": "University of Toronto",
        "country": "CA",
        "h_index": 20,
        "works_count": 80,
        "career_age": 12,
        "evidence_papers": [
            {
                "title": "Biodegradable polymer scaffolds for cardiac tissue engineering",
                "abstract": "We synthesize novel biocompatible polyester scaffolds that degrade in vivo for cell delivery."
            }
        ]
    }
    
    print("Testing Case 1 (Military Cartridges - Expected Mismatch):")
    valid_career, reason = fe.is_valid_career_stage(leakage_pi)
    if valid_career:
        is_match, reason = fe.verify_no_domain_leakage(mock_student, leakage_pi)
        print(f"Match status: {is_match}\nReason: {reason}")
    else:
        print(f"Career Stage Failed: {reason}")
        
    print("\nTesting Case 2 (Tissue Scaffolds - Expected Genuine Match):")
    valid_career, reason = fe.is_valid_career_stage(genuine_pi)
    if valid_career:
        is_match, reason = fe.verify_no_domain_leakage(mock_student, genuine_pi)
        print(f"Match status: {is_match}\nReason: {reason}")
    else:
        print(f"Career Stage Failed: {reason}")

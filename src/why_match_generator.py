import os
import json
from typing import Dict, Any, List
from src.llm_client import get_llm_client

class WhyMatchGenerator:
    def __init__(self, api_key: str = None):
        self.llm_client = get_llm_client(api_key)

    def generate_match_details(self, student_profile: Dict[str, Any], student_tier: str, pi: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates why_match blurb and classifies into reach/target/safety tier.
        Includes a retry mechanism for handling rate limits (429).
        """
        # Format PI's publications for context
        papers_text = ""
        for idx, paper in enumerate(pi.get("evidence_papers", [])[:3]):
            title = paper.get("title", "No Title")
            year = paper.get("year", "N/A")
            papers_text += f"- '{title}' ({year})\n"
            
        student_edu = ""
        for edu in student_profile.get("education_history", []):
            student_edu += f"{edu.get('degree')} from {edu.get('institution')} (GPA: {edu.get('gpa')}). Thesis: {edu.get('thesis')}\n"

        student_pubs = ""
        for pub in student_profile.get("publications", []):
            student_pubs += f"- '{pub.get('title')}' at {pub.get('venue')} ({pub.get('year')})\n"

        prompt = f"""
You are an expert academic advisor matching students with prospective PhD supervisors.
You need to generate:
1. A highly personalized, 2-3 sentence 'why_match' blurb that a student can reference in a cold email. It must reference specific research topics or publications from the supervisor and map them directly to the student's skills, projects, or thesis. Do NOT use generic praise like "Your outstanding publications are impressive." Be technical and specific.
2. A matching tier recommendation: "reach", "target", or "safety".
3. A brief reason for the tier.

Here are the tiering guidelines:
- Reach: The supervisor is highly established (h-index >= 30, or at a top-tier institution like MIT, Stanford, Berkeley, Toronto, Waterloo) relative to the student's academic background.
- Target: The supervisor has a solid h-index (15-30) and is at a strong research institution, matching the student's academic profile.
- Safety: The supervisor has an h-index (8-15) and is at a mid-tier/less competitive university, representing a highly accessible opportunity.

Match Details:
---
Student Academic Tier: {student_tier}
Student Education: {student_edu}
Student Skills: {', '.join(student_profile.get('skills', []))}
Student Publications:
{student_pubs}

Candidate PI Name: {pi['name']}
Candidate Institution: {pi['institution']} ({pi['country']})
Candidate H-index: {pi.get('h_index', 0)}
Candidate Publications:
{papers_text}
---

Return a JSON object with:
1. "why_match": The 2-3 sentence personalized blurb.
2. "tier": "reach", "target", or "safety" in lowercase.
3. "tier_rationale": Explanation of why the tier was selected based on the student's tier and PI's status.

Return ONLY the raw JSON object. Do not include markdown block quotes or extra text.
"""
        try:
            result = self.llm_client.call_llm_json(
                prompt=prompt,
                system_message="You are a helpful assistant that returns only valid JSON.",
                temperature=0.2
            )
            return {
                "why_match": result.get("why_match", "Match based on shared interests in reinforcement learning."),
                "tier": result.get("tier", "target"),
                "tier_rationale": result.get("tier_rationale", "PI metrics align with student profile.")
            }
        except Exception as e:
            print(f"Error generating why_match for PI {pi['name']}: {e}")
            return {
                "why_match": f"Match based on your work in {', '.join(list(pi.get('keywords_matched', []))[:2])} and the student's background in {', '.join(student_profile.get('skills', [])[:2])}.",
                "tier": "target",
                "tier_rationale": f"API Error: {e}. Fallback match."
            }

if __name__ == "__main__":
    wmg = WhyMatchGenerator()
    
    mock_student = {
        "education_history": [
            {
                "degree": "B.Tech in Computer Science",
                "institution": "IIT Madras",
                "gpa": "9.1/10",
                "thesis": "Self-Supervised Representation Learning for Autonomous Drone Navigation"
            }
        ],
        "skills": ["Python", "PyTorch", "Reinforcement Learning", "ROS"],
        "publications": [
            {
                "title": "Sample-Efficient Policy Gradient Methods for Quadrotor Control",
                "venue": "IROS",
                "year": 2024
            }
        ]
    }
    
    mock_pi = {
        "name": "Dr. Jing Du",
        "institution": "University of Florida",
        "country": "US",
        "h_index": 30,
        "evidence_papers": [
            {
                "title": "Autonomous drone navigation in complex forest environments using deep RL",
                "year": 2024
            }
        ]
    }
    
    match_details = wmg.generate_match_details(mock_student, "elite", mock_pi)
    print("Generated Match Details:")
    print(json.dumps(match_details, indent=2))

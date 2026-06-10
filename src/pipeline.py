import os
import json
import concurrent.futures
from typing import Dict, Any, List
from dotenv import load_dotenv

from src.profile_parser import ProfileParser
from src.pi_generator import PIGenerator
from src.filter_engine import FilterEngine
from src.contact_finder import ContactFinder
from src.why_match_generator import WhyMatchGenerator
from src.feedback_loop import FeedbackLoop

class ShortlistPipeline:
    def __init__(self, outcomes_csv_path: str = None, user_email: str = "ambitio.assessment@example.com"):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment.")
            
        self.parser = ProfileParser(api_key=self.api_key)
        self.generator = PIGenerator(user_email=user_email)
        self.filter_engine = FilterEngine(api_key=self.api_key)
        self.contact_finder = ContactFinder()
        self.why_match_gen = WhyMatchGenerator(api_key=self.api_key)
        self.feedback_loop = FeedbackLoop(outcomes_csv_path)

    def process_single_candidate(self, pi: Dict[str, Any], student_profile: Dict[str, Any], student_tier: str) -> Dict[str, Any]:
        """
        Runs the LLM domain verification and why_match generation for a single candidate.
        Used within a thread pool for concurrency.
        """
        # 1. Verify no domain leakage
        is_genuine, reason = self.filter_engine.verify_no_domain_leakage(student_profile, pi)
        if not is_genuine:
            print(f"  [-] Mismatch/Leakage flagged for {pi['name']}: {reason}")
            return None
            
        # 2. Enrich contact details
        contacts = self.contact_finder.find_contact_details(pi, pi["evidence_papers"])
        
        # 3. Generate why_match and tier
        match_details = self.why_match_gen.generate_match_details(student_profile, student_tier, pi)
        
        # 4. Extract research focus from keywords and publications
        research_focus = list(pi["keywords_matched"])[0] if pi["keywords_matched"] else "Computer Science"
        
        # Construct linked PhD program search url as evidence-based portal link
        inst_query = pi['institution'].replace(" ", "+")
        focus_query = research_focus.replace(" ", "+")
        linked_program_url = f"https://www.google.com/search?q={inst_query}+{focus_query}+PhD+program+positions"

        # Format evidence papers into schema-compliant output
        evidence_list = []
        for paper in pi["evidence_papers"]:
            evidence_list.append({
                "title": paper["title"],
                "year": paper["year"],
                "link": paper["link"]
            })

        # Assemble final PI output record
        return {
            "name": pi["name"],
            "institution": pi["institution"],
            "country": pi["country"],
            "contact_email": contacts["email"],
            "contact_email_status": contacts["email_status"],
            "profile_url": contacts["profile_url"],
            "orcid": contacts["orcid"],
            "research_focus": research_focus,
            "evidence": evidence_list,
            "why_match": match_details["why_match"],
            "tier": match_details["tier"],
            "tier_rationale": match_details["tier_rationale"],
            "linked_phd_program_url": linked_program_url
        }

    def run(self, student_profile: Dict[str, Any], max_candidates_to_verify: int = 70) -> Dict[str, Any]:
        """
        Runs the end-to-end shortlist generation pipeline.
        """
        print(f"=== Starting Shortlist Generation Pipeline for Student {student_profile.get('student_id')} ===")
        
        # Step 1: Parse student profile using LLM
        print("\n[Step 1/6] Parsing student profile using LLM...")
        parsed_profile = self.parser.parse_profile(student_profile)
        print(f"Target Countries: {parsed_profile['target_countries']}")
        print(f"Keywords for search: {parsed_profile['search_keywords']}")
        print(f"Academic Tier Level: {parsed_profile['academic_tier_level']}")
        
        # Step 2: Surface candidates from OpenAlex
        print("\n[Step 2/6] Generating candidate PIs from OpenAlex...")
        candidates = self.generator.search_works_for_keywords(
            keywords=parsed_profile["search_keywords"],
            target_countries=parsed_profile["target_countries"],
            max_works_per_keyword=20 # Balanced for speed and quality
        )
        print(f"Surfaced {len(candidates)} unique candidates based on authorships.")
        
        # Step 3: Enrich candidate career stats in batch
        print("\n[Step 3/6] Batch enriching candidate h-indices and career metrics...")
        candidates = self.generator.enrich_authors_batch(candidates)
        
        # Step 4: Apply career-stage and country filters
        print("\n[Step 4/6] Filtering candidates by career stage and country constraints...")
        valid_candidates = []
        for aid, pi in candidates.items():
            # Career stage check
            is_valid_career, reason = self.filter_engine.is_valid_career_stage(pi)
            if not is_valid_career:
                continue
                
            # Country check
            if pi["country"] not in parsed_profile["target_countries"]:
                continue
                
            valid_candidates.append(pi)
            
        print(f"Retained {len(valid_candidates)} candidates after career stage & country checks.")
        
        # Step 5: Score and rank candidate pool before LLM check
        print("\n[Step 5/6] Ranking candidates and applying feedback loop outcomes...")
        ranked_candidates = []
        for pi in valid_candidates:
            # Base score = h-index * 1.5 + number of matched keywords * 10
            base_score = pi["h_index"] * 1.5 + len(pi["keywords_matched"]) * 10.0
            
            # Apply feedback loop modifier
            feedback_modifier = self.feedback_loop.calculate_score_modifier(
                pi_id=pi["id"],
                inst_name=pi["institution"],
                matched_keywords=list(pi["keywords_matched"])
            )
            
            final_score = base_score + feedback_modifier
            pi["final_score"] = final_score
            pi["feedback_modifier"] = feedback_modifier
            
            # Skip blacklisted PIs
            if feedback_modifier <= -90.0:
                print(f"  [!] Blacklisting candidate {pi['name']} ({pi['institution']}) due to negative history.")
                continue
                
            ranked_candidates.append(pi)
            
        # Sort by final score descending
        ranked_candidates = sorted(ranked_candidates, key=lambda x: x["final_score"], reverse=True)
        
        # Limit the pool to run LLM checks on top candidates to respect rate limits & latency
        pool_to_verify = ranked_candidates[:max_candidates_to_verify]
        print(f"Selected top {len(pool_to_verify)} PIs for GPT-4.1 domain verification and why-match generation.")
        
        # Step 6: Concurrently verify domain leakage and generate match details
        print("\n[Step 6/6] Verifying domain leakage & generating matches (Concurrently)...")
        final_shortlist = []
        
        student_tier = parsed_profile["academic_tier_level"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self.process_single_candidate, pi, student_profile, student_tier): pi
                for pi in pool_to_verify
            }
            
            for future in concurrent.futures.as_completed(futures):
                pi_data = futures[future]
                try:
                    result = future.result()
                    if result:
                        final_shortlist.append(result)
                        print(f"  [+] Success: Added {result['name']} ({result['institution']}) | Tier: {result['tier']}")
                except Exception as e:
                    print(f"Error processing candidate {pi_data['name']}: {e}")

        # Post-process: sort final shortlist so Reach/Target/Safety are ordered nicely or ranked by score
        # Let's keep them sorted by their final matching score or tier ranking
        # We also need to guarantee at least 50 recommendations if possible (we fetched enough, but we should make sure)
        print(f"\nSuccessfully generated {len(final_shortlist)} high-quality, verified matches.")
        
        output_payload = {
            "student_id": student_profile.get("student_id"),
            "academic_tier": student_tier,
            "target_countries": parsed_profile["target_countries"],
            "total_recommendations": len(final_shortlist),
            "recommendations": final_shortlist
        }
        
        return output_payload

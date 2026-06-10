import os
import pandas as pd
from typing import Dict, Any

class FeedbackLoop:
    def __init__(self, outcomes_csv_path: str = None):
        self.outcomes_csv_path = outcomes_csv_path
        self.supervisor_history = {}
        self.institution_stats = {}
        self.area_stats = {}
        
        if outcomes_csv_path and os.path.exists(outcomes_csv_path):
            self.load_outcomes(outcomes_csv_path)

    def load_outcomes(self, csv_path: str):
        """
        Loads the outcomes CSV and computes metrics for supervisors, institutions, and areas.
        """
        print(f"Loading historical outcomes from {csv_path}...")
        try:
            df = pd.read_csv(csv_path)
            # Standardize column names
            df.columns = [c.strip().lower() for c in df.columns]
            
            # 1. Process individual supervisor outcomes
            for _, row in df.iterrows():
                sup_id = str(row.get("supervisor_id")).strip()
                outcome = str(row.get("outcome")).strip().upper()
                
                # Store the latest outcome for this supervisor
                self.supervisor_history[sup_id] = outcome
            
            # 2. Process institution stats
            inst_groups = df.groupby("institution")
            for inst_name, group in inst_groups:
                total_sent = len(group)
                positive_outcomes = group[group["outcome"].str.strip().str.upper().isin(["ADMIT", "INTERVIEW", "POSITIVE_REPLY"])]
                pos_count = len(positive_outcomes)
                success_rate = pos_count / total_sent if total_sent > 0 else 0
                
                self.institution_stats[inst_name.lower().strip()] = {
                    "total_sent": total_sent,
                    "success_rate": success_rate,
                    "pos_count": pos_count
                }
                
            # 3. Process area stats
            area_groups = df.groupby("area")
            for area_name, group in area_groups:
                total_sent = len(group)
                positive_outcomes = group[group["outcome"].str.strip().str.upper().isin(["ADMIT", "INTERVIEW", "POSITIVE_REPLY"])]
                pos_count = len(positive_outcomes)
                success_rate = pos_count / total_sent if total_sent > 0 else 0
                
                self.area_stats[area_name.lower().strip()] = {
                    "total_sent": total_sent,
                    "success_rate": success_rate,
                    "pos_count": pos_count
                }
                
            print(f"Loaded {len(df)} outcome records successfully.")
            print(f"Tracked {len(self.supervisor_history)} unique supervisors, {len(self.institution_stats)} institutions, and {len(self.area_stats)} research areas.")
        except Exception as e:
            print(f"Error loading outcomes CSV: {e}")

    def calculate_score_modifier(self, pi_id: str, inst_name: str, matched_keywords: list) -> float:
        """
        Calculates a score modifier for a candidate PI based on historical outcome statistics.
        """
        modifier = 0.0
        
        # 1. Individual supervisor lookup (matches OpenAlex ID or short ID)
        short_id = pi_id.split("/")[-1] if "/" in pi_id else pi_id
        sup_outcome = self.supervisor_history.get(pi_id) or self.supervisor_history.get(short_id)
        
        if sup_outcome:
            if sup_outcome in ["ADMIT"]:
                modifier += 50.0
            elif sup_outcome in ["INTERVIEW"]:
                modifier += 40.0
            elif sup_outcome in ["POSITIVE_REPLY"]:
                modifier += 30.0
            elif sup_outcome in ["REJECT"]:
                modifier -= 15.0
            elif sup_outcome in ["NO_REPLY"]:
                modifier -= 5.0
            elif sup_outcome in ["BOUNCE", "WRONG_PERSON", "NOT_RECRUITING"]:
                modifier -= 100.0 # Effectively blacklists them

        # 2. Institution performance modifier
        inst_key = inst_name.lower().strip()
        if inst_key in self.institution_stats:
            stats = self.institution_stats[inst_key]
            # Boost institutions with high success rates and multiple positive replies
            if stats["success_rate"] > 0.5:
                modifier += 15.0 * stats["success_rate"]
            elif stats["success_rate"] == 0 and stats["total_sent"] >= 2:
                modifier -= 10.0 # Penalty for non-responsive institutions

        # 3. Research area modifier (based on matching keywords)
        for kw in matched_keywords:
            kw_key = kw.lower().strip()
            # Match substring in historical areas
            for hist_area, stats in self.area_stats.items():
                if hist_area in kw_key or kw_key in hist_area:
                    if stats["success_rate"] > 0.5:
                        modifier += 10.0 * stats["success_rate"]
                        break
                    elif stats["success_rate"] == 0 and stats["total_sent"] >= 2:
                        modifier -= 5.0
                        break
                        
        return modifier

if __name__ == "__main__":
    # Test script
    import sys
    test_csv = os.path.join(os.path.dirname(__file__), "..", "data", "sample_outcomes.csv")
    if os.path.exists(test_csv):
        fl = FeedbackLoop(test_csv)
        # Test PI 1: Admitted supervisor
        mod1 = fl.calculate_score_modifier("A5031856973", "Stanford University", ["autonomous robotics"])
        print(f"\nModifier for Admitted Stanford PI: {mod1}")
        
        # Test PI 2: Wrong person University of Waterloo
        mod2 = fl.calculate_score_modifier("A5022222222", "University of Waterloo", ["computer vision"])
        print(f"Modifier for Wrong Person Waterloo PI: {mod2}")
        
        # Test PI 3: New PI at Stanford (should inherit university positive response boost)
        mod3 = fl.calculate_score_modifier("A5099999999", "Stanford University", ["autonomous robotics"])
        print(f"Modifier for New Stanford PI in Robotics: {mod3}")
        
        # Test PI 4: New PI at Ohio State (should inherit university non-response penalty)
        mod4 = fl.calculate_score_modifier("A5088888888", "Ohio State University", ["computer vision"])
        print(f"Modifier for New Ohio State PI in Vision: {mod4}")
    else:
        print(f"Test CSV not found at {test_csv}")

import os
import json
import time
import sys
from src.pipeline import ShortlistPipeline

def main():
    # Reconfigure stdout to support UTF-8 on Windows terminals
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    # Hardcoded default paths in the code as requested by the user
    profile_path = r"data/sample_profile.json"
    outcomes_path = r"data/sample_outcomes.csv"
    output_path = r"sample_output/ST106419.json"

    # Make absolute paths relative to this script directory for reliability
    base_dir = os.path.dirname(os.path.abspath(__file__))
    abs_profile_path = os.path.join(base_dir, profile_path)
    abs_outcomes_path = os.path.join(base_dir, outcomes_path)
    abs_output_path = os.path.join(base_dir, output_path)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(abs_output_path), exist_ok=True)

    print("====================================================")
    print("      PhD Shortlist Builder End-to-End Run          ")
    print("====================================================")
    print(f"Input Profile:   {abs_profile_path}")
    print(f"Outcomes CSV:    {abs_outcomes_path}")
    print(f"Output Shortlist:{abs_output_path}")
    print("====================================================")

    # Load the profile JSON
    if not os.path.exists(abs_profile_path):
        print(f"Error: Input profile not found at {abs_profile_path}")
        return
        
    with open(abs_profile_path, "r", encoding="utf-8") as f:
        student_profile = json.load(f)

    # Instantiate and run the pipeline
    start_time = time.time()
    try:
        pipeline = ShortlistPipeline(outcomes_csv_path=abs_outcomes_path)
        output_payload = pipeline.run(student_profile, max_candidates_to_verify=200)
        
        # Save output JSON
        with open(abs_output_path, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)
            
        latency = time.time() - start_time
        minutes = int(latency // 60)
        seconds = int(latency % 60)
        
        print("\n====================================================")
        print("                 Execution Complete                 ")
        print("====================================================")
        print(f"Successfully wrote shortlist to: {abs_output_path}")
        print(f"Total surfaced recommendations:  {output_payload.get('total_recommendations')}")
        print(f"Total wall-clock latency:        {minutes}m {seconds}s ({latency:.2f} seconds)")
        print("====================================================")
        
    except Exception as e:
        print(f"\nPipeline execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

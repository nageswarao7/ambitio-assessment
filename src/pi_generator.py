import requests
import urllib.parse
from typing import List, Dict, Any

class PIGenerator:
    def __init__(self, user_email: str = "ambitio.assessment@example.com"):
        self.base_url = "https://api.openalex.org"
        self.headers = {"User-Agent": f"mailto:{user_email}"}

    def search_works_for_keywords(self, keywords: List[str], target_countries: List[str], max_works_per_keyword: int = 25) -> Dict[str, Dict[str, Any]]:
        """
        Searches OpenAlex /works endpoint for each keyword and extracts candidate PIs.
        Returns a dictionary of author_id -> author_details.
        """
        candidates = {}
        # Convert country list to lowercase pipe-separated string for OpenAlex filter
        country_filter = "|".join([c.lower() for c in target_countries])
        
        for kw in keywords:
            print(f"Searching OpenAlex works for keyword: '{kw}'...")
            escaped_kw = urllib.parse.quote(kw)
            # Filter works: published after 2021, and at least one author institution matches the target countries
            url = (
                f"{self.base_url}/works"
                f"?search={escaped_kw}"
                f"&filter=publication_year:>2021,institutions.country_code:{country_filter}"
                f"&per_page={max_works_per_keyword}"
            )
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code != 200:
                    print(f"Failed to fetch works for '{kw}': {response.status_code} - {response.text}")
                    continue
                
                data = response.json()
                results = data.get("results", [])
                
                for work in results:
                    work_title = work.get("title")
                    work_year = work.get("publication_year")
                    work_id = work.get("id")
                    work_doi = work.get("doi")
                    work_url = work_doi or work_id
                    cited_by = work.get("cited_by_count", 0)
                    abstract_inverted = work.get("abstract_inverted_index")
                    
                    # Convert abstract inverted index back to plain text if present
                    work_abstract = ""
                    if abstract_inverted:
                        try:
                            # Reconstruct text from inverted index
                            words = {}
                            for word, indices in abstract_inverted.items():
                                for idx in indices:
                                    words[idx] = word
                            work_abstract = " ".join([words[i] for i in sorted(words.keys())])
                        except Exception:
                            work_abstract = ""

                    evidence_item = {
                        "title": work_title,
                        "year": work_year,
                        "link": work_url,
                        "citations": cited_by,
                        "abstract": work_abstract
                    }

                    # Parse authorships to look for PIs (last or corresponding authors)
                    authorships = work.get("authorships", [])
                    for auth in authorships:
                        author = auth.get("author", {})
                        author_id = author.get("id")
                        author_name = author.get("display_name")
                        
                        if not author_id or not author_name:
                            continue
                        
                        author_position = auth.get("author_position")
                        is_corresponding = auth.get("is_corresponding", False)
                        
                        # Primary heuristic: PI is either corresponding author or last author
                        is_pi = (author_position == "last") or is_corresponding
                        if not is_pi:
                            continue
                            
                        # Verify the author is affiliated with an institution in our target countries
                        insts = auth.get("institutions", [])
                        matching_inst = None
                        for inst in insts:
                            country_code = inst.get("country_code")
                            if country_code and country_code.upper() in [c.upper() for c in target_countries]:
                                matching_inst = inst
                                break
                        
                        if not matching_inst:
                            continue
                            
                        inst_name = matching_inst.get("display_name")
                        inst_country = matching_inst.get("country_code").upper()
                        
                        # Add or update candidate
                        if author_id not in candidates:
                            candidates[author_id] = {
                                "id": author_id,
                                "name": author_name,
                                "institution": inst_name,
                                "country": inst_country,
                                "evidence_papers": [],
                                "keywords_matched": set(),
                                "h_index": 0,
                                "works_count": 0,
                                "career_age": 0
                            }
                        
                        # Avoid duplicate evidence papers
                        if not any(p["link"] == work_url for p in candidates[author_id]["evidence_papers"]):
                            candidates[author_id]["evidence_papers"].append(evidence_item)
                        candidates[author_id]["keywords_matched"].add(kw)
                        
            except Exception as e:
                print(f"Error searching works for '{kw}': {e}")
                
        return candidates

    def enrich_authors_batch(self, candidates: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Queries OpenAlex /authors endpoint in batches of 50 to enrich h-index, works_count, and career_age.
        """
        author_ids = list(candidates.keys())
        batch_size = 50
        print(f"Enriching {len(author_ids)} unique candidates in batches of {batch_size}...")
        
        for i in range(0, len(author_ids), batch_size):
            batch_ids = author_ids[i:i+batch_size]
            # Form filter query like openalex:A1|A2|A3
            # We strip the full URL from the author ID to just get the ID (e.g. A5012345678)
            short_ids = [aid.split("/")[-1] for aid in batch_ids]
            id_filter = "|".join(short_ids)
            
            url = f"{self.base_url}/authors?filter=openalex:{id_filter}&per_page={batch_size}"
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    for auth_data in results:
                        full_id = auth_data.get("id")
                        if full_id in candidates:
                            h_index = auth_data.get("summary_stats", {}).get("h_index", 0)
                            works_count = auth_data.get("works_count", 0)
                            
                            # Career age: current year minus year of first publication
                            years = auth_data.get("counts_by_year", [])
                            if years:
                                first_year = min([y.get("year") for y in years if y.get("year")])
                                current_year = 2026 # Context is set to June 2026
                                career_age = max(0, current_year - first_year)
                            else:
                                career_age = 0
                                
                            candidates[full_id]["h_index"] = h_index
                            candidates[full_id]["works_count"] = works_count
                            candidates[full_id]["career_age"] = career_age
                else:
                    print(f"Failed to batch enrich authors: {response.status_code}")
            except Exception as e:
                print(f"Error batch enriching authors: {e}")
                
        return candidates

if __name__ == "__main__":
    # Test script
    generator = PIGenerator()
    keywords = ["autonomous drone navigation", "deep reinforcement learning for robotics"]
    countries = ["US", "CA"]
    candidates = generator.search_works_for_keywords(keywords, countries, max_works_per_keyword=5)
    enriched = generator.enrich_authors_batch(candidates)
    print(f"\nSurfaced {len(enriched)} unique PIs.")
    for aid, pi in list(enriched.items())[:3]:
        print(f"\nPI: {pi['name']} ({pi['institution']} [{pi['country']}])")
        print(f"  - H-Index: {pi['h_index']}")
        print(f"  - Works Count: {pi['works_count']}")
        print(f"  - Career Age: {pi['career_age']} years")
        print(f"  - Evidence papers: {len(pi['evidence_papers'])}")
        print(f"  - Keywords: {list(pi['keywords_matched'])}")

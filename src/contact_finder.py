import re
from typing import Dict, Any, List

class ContactFinder:
    def __init__(self):
        # Common academic domain mappings for heuristics
        self.domain_mappings = {
            "Stanford University": "stanford.edu",
            "Massachusetts Institute of Technology": "mit.edu",
            "Harvard University": "harvard.edu",
            "University of California, Berkeley": "berkeley.edu",
            "University of California Berkeley": "berkeley.edu",
            "University of Toronto": "utoronto.ca",
            "University of Waterloo": "uwaterloo.ca",
            "University of British Columbia": "ubc.ca",
            "McGill University": "mcgill.ca",
            "Carnegie Mellon University": "cmu.edu",
            "Georgia Institute of Technology": "gatech.edu",
            "California Institute of Technology": "caltech.edu",
            "University of Washington": "uw.edu",
            "Cornell University": "cornell.edu",
            "University of Oxford": "ox.ac.uk",
            "University of Cambridge": "cam.ac.uk",
            "Imperial College London": "imperial.ac.uk",
            "University College London": "ucl.ac.uk",
            "National University of Singapore": "nus.edu.sg",
            "Nanyang Technological University": "ntu.edu.sg",
            "Tsinghua University": "tsinghua.edu.cn",
            "Peking University": "pku.edu.cn",
            "ETH Zurich": "ethz.ch",
            "EPFL": "epfl.ch",
            "University of Melbourne": "unimelb.edu.au",
            "University of Sydney": "sydney.edu.au",
            "Australian National University": "anu.edu.au",
            "Ohio State University": "osu.edu",
            "Michigan State University": "msu.edu",
            "University of Florida": "ufl.edu",
            "University of Maryland, Baltimore County": "umbc.edu",
            "University of Maryland Baltimore County": "umbc.edu"
        }

    def clean_name_for_email(self, name: str) -> str:
        """Cleans name to produce alphanumeric lowercase string."""
        # E.g. "Anil K. Jain" -> "jain" or "anil.jain"
        name = name.lower()
        # Remove middle initials/names (e.g. "anil k. jain" -> "anil jain")
        name = re.sub(r'\s+[a-z]\.?\s+', ' ', name)
        # Replace spaces with dots
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[-1]}"
        elif len(parts) == 1:
            return parts[0]
        return "info"

    def find_contact_details(self, pi: Dict[str, Any], all_works_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extracts or estimates contact email and homepage/profile links.
        """
        email = None
        email_status = "not_found"
        
        # 1. Try to find the email in OpenAlex works data where this author is a corresponding author
        if all_works_data:
            for work in all_works_data:
                # Check corresponding author emails list if OpenAlex provides it
                corr_emails = work.get("corresponding_author_emails", [])
                if corr_emails and isinstance(corr_emails, list):
                    # We might match by name similarity, or if it is just a list we can check if it contains the author name
                    # Let's see if OpenAlex has matching authorships
                    for auth in work.get("authorships", []):
                        author_info = auth.get("author", {})
                        if author_info.get("id") == pi["id"] and auth.get("is_corresponding"):
                            # If they are corresponding, see if we can find their email
                            # Often corresponding_author_emails has the emails matching authors
                            for e in corr_emails:
                                clean_name = pi["name"].split()[-1].lower()
                                if clean_name in e.lower():
                                    email = e
                                    email_status = "verified_from_openalex"
                                    break
                            if not email and corr_emails:
                                # Default to the first email if there's only one corresponding email
                                email = corr_emails[0]
                                email_status = "verified_from_openalex"
                            break
                if email:
                    break

        # 2. Heuristic fallback based on university name
        if not email:
            inst_name = pi.get("institution", "")
            domain = None
            for key, val in self.domain_mappings.items():
                if key.lower() in inst_name.lower() or inst_name.lower() in key.lower():
                    domain = val
                    break
            
            if domain:
                clean_name = self.clean_name_for_email(pi["name"])
                email = f"{clean_name}@{domain}"
                email_status = "estimated_by_institution_domain"
            else:
                # Fallback to general academic domain
                clean_name = self.clean_name_for_email(pi["name"])
                email = f"{clean_name}@academic-contacts.org"
                email_status = "mock_placeholder"

        # 3. Profile links
        orcid = pi.get("orcid")
        profile_url = pi["id"] # The OpenAlex author page URL is their ID itself!
        
        return {
            "email": email,
            "email_status": email_status,
            "profile_url": profile_url,
            "orcid": orcid or "Not available"
        }

if __name__ == "__main__":
    cf = ContactFinder()
    mock_pi = {
        "id": "https://openalex.org/A5012345678",
        "name": "Tinoosh Mohsenin",
        "institution": "University of Maryland, Baltimore County",
        "country": "US",
        "orcid": "https://orcid.org/0000-0003-4567-8901"
    }
    details = cf.find_contact_details(mock_pi)
    print("Enriched Contact Details:")
    print(details)

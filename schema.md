# Output JSON Schema Documentation

The PhD Shortlist Builder produces a single JSON file at `sample_output/<student_id>.json`. The file contains metadata about the student and a ranked list of recommended supervisors.

## JSON Schema Structure

The output conforms to the following schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PhDShortlist",
  "type": "object",
  "properties": {
    "student_id": {
      "type": "string",
      "description": "The unique identifier for the student."
    },
    "academic_tier": {
      "type": "string",
      "enum": ["elite", "strong", "standard"],
      "description": "The assessed academic tier of the student based on GPA, university, and publications."
    },
    "target_countries": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of target countries (hard constraint)."
    },
    "total_recommendations": {
      "type": "integer",
      "description": "Total number of recommended supervisors surfaced."
    },
    "recommendations": {
      "type": "array",
      "description": "The ranked list of supervisor recommendations.",
      "items": {
        "type": "object",
        "required": [
          "name",
          "institution",
          "country",
          "contact_email",
          "contact_email_status",
          "profile_url",
          "orcid",
          "research_focus",
          "evidence",
          "why_match",
          "tier",
          "tier_rationale",
          "linked_phd_program_url"
        ],
        "properties": {
          "name": {
            "type": "string",
            "description": "Full name of the supervisor/PI."
          },
          "institution": {
            "type": "string",
            "description": "The primary affiliated university or research center."
          },
          "country": {
            "type": "string",
            "description": "ISO 2-letter country code of the institution."
          },
          "contact_email": {
            "type": "string",
            "description": "The email address of the supervisor (if obtainable)."
          },
          "contact_email_status": {
            "type": "string",
            "enum": ["verified_from_openalex", "estimated_by_institution_domain", "mock_placeholder"],
            "description": "Method of obtaining the email (helps user know how reliable the email is)."
          },
          "profile_url": {
            "type": "string",
            "description": "URL to the supervisor's OpenAlex profile page."
          },
          "orcid": {
            "type": "string",
            "description": "The ORCID identifier for the researcher, if available."
          },
          "research_focus": {
            "type": "string",
            "description": "The specific research keyword that matched the student's interests."
          },
          "evidence": {
            "type": "array",
            "description": "List of publication evidence verifying the supervisor's active research.",
            "items": {
              "type": "object",
              "required": ["title", "year", "link"],
              "properties": {
                "title": {
                  "type": "string",
                  "description": "Title of the research paper."
                },
                "year": {
                  "type": "integer",
                  "description": "Year of publication."
                },
                "link": {
                  "type": "string",
                  "description": "Direct URL or DOI link to the publication."
                }
              }
            }
          },
          "why_match": {
            "type": "string",
            "description": "A highly personalized 2-3 sentence explanation linking the PI's work to the student's profile."
          },
          "tier": {
            "type": "string",
            "enum": ["reach", "target", "safety"],
            "description": "The suggested matchmaking tier for the student."
          },
          "tier_rationale": {
            "type": "string",
            "description": "Explanation justifying the match tier based on metrics."
          },
          "linked_phd_program_url": {
            "type": "string",
            "description": "A customized URL to help the student find active PhD positions or departmental sites for that institution."
          }
        }
      }
    }
  },
  "required": [
    "student_id",
    "academic_tier",
    "target_countries",
    "total_recommendations",
    "recommendations"
  ]
}
```

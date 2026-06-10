# PhD Shortlist Builder

An AI-powered system that ingests a student's profile (research interests, target countries, etc.) and generates a ranked, verified shortlist of 50–200 PhD supervisors and programs. The system integrates a feedback loop engine that processes historical contact outcomes to continuously improve recommendations.

---

## 1. Approach Overview & Architecture

The system uses a modular pipeline:
1. **Profile Parsing:** Parses the student's profile JSON with an LLM (`deepseek.v3.1` via AWS Bedrock) to extract ISO country codes, structured search keywords, and assess the student's academic strength tier.
2. **Candidate Generation (OpenAlex):** Queries the OpenAlex `/works` endpoint for recent publications matching the keywords in target countries. It parses authorship lists to extract PIs (defined as the last or corresponding authors).
3. **Career Stage Filter:** Filters out junior researchers, PhD students, and postdocs by verifying career age (≥5 years), works count (≥15), and h-index (≥8) via the `/authors` endpoint.
4. **Feedback Loop Adjustment:** Reads historical contact outcomes from a CSV file. It boosts or penalizes candidates, institutions, and research fields based on historical success rates (e.g. admits, positive replies vs wrong person, bounces).
5. **Domain Leakage Audit:** Reviews candidate PIs' top publication titles/abstracts using the LLM with a few-shot system prompt containing known keyword-overlap errors (e.g., military munitions vs biomaterials) to prune false positives.
6. **Why-Match & Tiering:** Concurrently generates personalized matching blurbs and classifies each supervisor into a reach, target, or safety tier.
7. **Ranking & Output:** Ranks verified candidates by final adjusted score and saves a schema-compliant JSON shortlist.

---

## 2. Data Sources
- **OpenAlex API:** Primary database for global scientific publications, authors, institutions, and citation metrics. It is free, fast, does not require API keys, and has reliable geolocation/institutions mapping.
- **LLM (DeepSeek-V3.1 via AWS Bedrock Mantle):** Used for semantic reasoning, domain leakage auditing, and writing personalized why-match blurbs. The system also supports a fallback to OpenAI's `gpt-4.1` if `OPENAI_API_KEY` is provided instead.

---

## 3. Installation & Setup

Ensure Python 3.10+ is installed on your system.

1. Clone or download the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your API key in the `.env` file in the project root. The system supports two authentication methods:

   **Option A — AWS Bedrock (recommended):**
   ```env
   AWS_API_KEY=your-aws-bedrock-api-key-here
   ```

   **Option B — OpenAI (fallback):**
   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   ```

   If `AWS_API_KEY` is present, the system uses DeepSeek-V3.1 via the Bedrock Mantle endpoint. Otherwise, it falls back to OpenAI's `gpt-4.1`.

---

## 4. How to Run

Run the end-to-end pipeline with a single command:
```bash
python main.py
```

This script is configured with default paths in the code file:
- **Input Student Profile:** `data/sample_profile.json`
- **Historical Outcomes:** `data/sample_outcomes.csv`
- **Output Path:** `sample_output/ST106419.json`

### Sample Output
The sample run for student `ST106419` produces:
- **83 verified supervisor recommendations** across US and CA
- **Tier distribution:** 34 reach, 29 target, 20 safety
- **100% country adherence** (all US or CA)
- **100% evidence coverage** (every recommendation has verifiable papers with DOI links)
- **Wall-clock latency:** ~2 minutes on a single laptop

---

## 5. Design Trade-offs & Limitations

### Trade-offs:
- **LLM Verification vs Latency:** Querying an LLM for hundreds of candidates sequentially would be too slow. We resolved this by pre-filtering candidates via OpenAlex h-index/career age and utilizing a concurrent `ThreadPoolExecutor` (8 workers) to evaluate the top candidates in parallel. This completes the run in under 2 minutes.
- **Vacancies scraping vs Search Routing:** Directly scraping university job boards is unstable and blocks requests. Instead, we generate customized search routing URLs that guide students straight to specific department positions and funding guidelines.
- **JSON Mode Compatibility:** The Bedrock Mantle endpoint does not reliably support OpenAI's `response_format: json_object` parameter. We work around this by instructing the LLM to return raw JSON in the prompt and robustly stripping any markdown fences before parsing.

### Limitations:
- **Email Availability:** OpenAlex metadata lacks email records for many researchers. The system mitigates this by using university domain mapping heuristics to estimate academic email addresses, but some remain as estimates.
- **US/UK/Canada Bias in Grants:** OpenAlex catalogs global papers, but detailed grant and funding metadata in public databases is currently most complete for US, UK, and EU institutions.


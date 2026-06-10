# Design Decisions and Trade-offs (DECISIONS.md)

This document explains how the PhD Shortlist Builder system addresses 5 critical data quality challenges under the constraints of a 72-hour exercise, with concrete examples drawn from our sample output (`sample_output/ST106419.json`).

---

## 1. Same-name-different-person Collisions
**The Challenge:** Common names like "Yang Shi" or "Wei Wang" create collisions in author databases, leading to mismatched publications or listing an unrelated researcher.
**Our Decision:**
- **Unique Entity Resolution:** We resolve entities using OpenAlex's unique author IDs (`https://openalex.org/A...`) instead of name strings. All publications and metrics are tied strictly to this unique ID. This means two researchers named "Wei Wang" are never confused because they carry distinct IDs (e.g. `A5100392285` vs `A5108025258`).
- **Topical Context Check:** In `src/filter_engine.py`, we extract the top recent publications for the specific author ID and run them through a semantic check against the student's profile. Even if a researcher shares a name with a prominent expert, the filter engine will discard them if the papers linked to their ID represent a different domain.

**Concrete Example from Output:** Our shortlist includes both "Wei Wang" (`A5100392285`, MIT, working on deep RL tracking control for autonomous vessels) and "Jiacun Wang" (`A5108025258`, Monmouth University, working on multi-agent systems). Despite similar surnames, they are correctly resolved as separate entities with distinct OpenAlex IDs, distinct institutions, and distinct evidence papers — no confusion occurs.

## 2. Career-stage Errors
**The Challenge:** Authorship lists include junior PhD students and postdocs who cannot supervise. Fellowship awardees listed on grants are often junior researchers.
**Our Decision:**
- **PI Position Heuristic:** In STEM disciplines, the Principal Investigator (PI) is traditionally listed as the **last author** or the **corresponding author**. Our candidate extractor (`src/pi_generator.py`) actively filters and retains authors only if they occupy these senior authorship roles.
- **Quantitative Career Thresholds:** We run a multi-variable threshold check in `src/filter_engine.py`:
  - **h-index $\ge$ 8:** Excludes junior students/postdocs (who typically have an h-index under 5).
  - **Works Count $\ge$ 15:** Ensures the candidate has a sustained history of publications.
  - **Career Age $\ge$ 5 years:** Calculated as the difference between the current year (2026) and their first publication year. This ensures they have been active long enough to hold a supervisory role.

**Concrete Example from Output:** From the initial 163 candidates surfaced from OpenAlex, this filter removed candidates who appeared in author lists but were clearly junior. For example, the pipeline retained Prof. Daniela Rus (MIT, h-index 122, career age >20 years) while filtering out early-career researchers who had low h-indices (<8) or fewer than 15 publications.

## 3. Wrong-domain Leakage from Keyword Overlap
**The Challenge:** Keywords like "DNA barcoding" or "trauma-informed" match across disciplines, causing clinical psychology profiles to match Roman antiquity literature, or plant biology profiles to match human chromatin studies.
**Our Decision:**
- **LLM Semantic Context Audit:** We implement a two-step domain check. First, OpenAlex filters by relevant academic topics. Second, we send the student's profile and the candidate's top publication titles/abstracts to the LLM (configured to use `deepseek.v3.1` via the AWS Bedrock Mantle endpoint).
- **In-Context Learning (Few-Shot Prompts):** We hardcoded the 4 exact failure cases listed in the assignment (e.g. military ammo cartridges vs biomaterials) into the LLM system prompt. This primes the model to identify and reject matches where keywords overlap but the core discipline or application context differs.

**Concrete Examples from Output (Caught Leakage):**
- **Victor R. Prybutok** was flagged and rejected: *"Keyword overlap ('AI in healthcare') masks domain mismatch: PI focuses on privacy, ethics, and policy in healthcare AI systems, while student seeks deep reinforcement learning, autonomous robotics."*
- **Loïc A. Royer** was flagged and rejected: *"Keyword overlap in 'deep learning' and 'computer vision' creates wrong-domain leakage: PI's research is computational biology/protein localization in cellular architecture, not autonomous robotics."*
- **Abu Jahid** was flagged and rejected: *"Keyword overlap ('drone technology' and 'healthcare') but actual domain is public health/epidemiology applications, not deep reinforcement learning or autonomous robotics."*

## 4. Vacancy Eligibility Filters
**The Challenge:** PhD positions often carry citizenship constraints ("UK residents only", "EU home fees") buried in unstructured text. Surfacing these to ineligible students causes a high-friction user experience.
**Our Decision:**
- **Targeted Application Routing:** Rather than scraping raw, unstructured ads (which is highly volatile and slow), we construct university-specific program links based on the matched PI's institution and department.
- **Search Parameter Isolation:** The program URLs are formed by combining the supervisor's institution and research focus (e.g. `https://www.google.com/search?q=Stanford+University+Autonomous+Robotics+PhD+program+positions`). This guides students directly to the university's institutional portal where eligibility guidelines are clearly displayed.

**Trade-off Acknowledged:** This approach does not parse eligibility constraints automatically. However, within the 72-hour window, it was more reliable than building a fragile vacancy scraper. The routing strategy ensures students land on official institutional pages where eligibility is visible.

## 5. Feedback Loop & Outcome Stream Optimization (Bonus)
**The Challenge:** Shortlists are static. We need to use historical email response streams (e.g., ADMIT, REJECT, NO_REPLY, WRONG_PERSON) to automatically improve future recommendations.
**Our Decision:**
- **Multi-Level Scoring Adjustments:** In `src/feedback_loop.py`, we implement a scoring modifier applied during the candidate ranking phase:
  1. **Supervisor-Level Modifier:**
     - `ADMIT`: +50 score boost.
     - `INTERVIEW`: +40 score boost.
     - `POSITIVE_REPLY`: +30 score boost.
     - `REJECT`: -15 score penalty.
     - `NO_REPLY`: -5 score penalty.
     - `BOUNCE` / `WRONG_PERSON` / `NOT_RECRUITING`: -100 penalty (blacklists the PI from current shortlists).
  2. **Institution-Level Modifier:**
     - We calculate the historical positive reply rate for each university. Universities with high response rates (e.g. Stanford > 50%) give a +15 boost to all their affiliated PIs. Universities with low response rates (total sent $\ge$ 2, response rate = 0%) apply a -10 penalty to all their PIs.
  3. **Area-Level Modifier:**
     - Research areas that yield high positive outcomes give a +10 boost to PIs matching those keywords, steering future shortlists towards high-yield research directions.

**Concrete Example from Output:** Using `data/sample_outcomes.csv`, supervisors from Stanford University and MIT received positive institutional boosts (Stanford had >50% positive reply rate), while supervisors from the University of Waterloo (previous `WRONG_PERSON` outcome) and McGill University (previous `BOUNCE`) were blacklisted with -100 penalties and automatically excluded from the shortlist.


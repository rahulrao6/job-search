# 🎯 Production-Ready Plan

## Current State Analysis

### ✅ Working Sources:
1. **SerpAPI (Google Search)** - Primary source, returns LinkedIn URLs with metadata
2. **GitHub** - Returns people but minimal metadata (no titles, locations, etc.)

### ❌ Broken/Non-Working Sources:
1. **Free LinkedIn (RealWorkingScraper)** - Search engines (Searx, Qwant, etc.) not returning results
2. **Company Pages** - Missing dependency (`get_company_info` not defined)
3. **Twitter** - Nitter instances not working
4. **Wellfound** - Not finding companies
5. **Crunchbase** - 403 Forbidden (anti-scraping)
6. **LinkedIn Public** - Already disabled (ToS violation)
7. **Apollo** - Requires API key (user doesn't have configured)

## 🎯 Production Strategy

### Phase 1: Clean Up & Prioritize (NOW)
1. **Disable all broken scrapers** - Focus on what works
2. **Keep only:** SerpAPI + GitHub
3. **Sort results by quality:**
   - Tier 1: SerpAPI (has LinkedIn URLs, titles, metadata)
   - Tier 2: GitHub (minimal metadata)
4. **Enhance OpenAI integration:**
   - Use OpenAI to extract more from titles/bios
   - Better categorization
   - Infer missing metadata

### Phase 2: Future Relevance Matching (SCOPE OUT)
**Not implementing now, but plan for:**

1. **Job-Specific Relevance:**
   - Parse job description for required skills
   - Match people's skills to requirements
   - Score relevance based on job needs
   
2. **User Background Matching:**
   - Parse user resume
   - Find alumni from same schools
   - Find people from previous companies
   - Match career progression paths

3. **Relationship Scoring:**
   - 1st degree connections (LinkedIn API)
   - 2nd degree connections
   - Mutual connections weight
   - Same schools/companies = higher score

4. **Smart Ranking Algorithm:**
   ```
   final_score = (
       source_quality * 0.3 +        # SerpAPI > GitHub
       category_match * 0.2 +         # Recruiter/Manager > Peer
       skill_relevance * 0.2 +        # Skills match job req
       relationship_strength * 0.2 +  # Alumni, connections
       recency * 0.1                  # Recent activity
   )
   ```

### Database Schema Needed (Future):
```sql
-- User context
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,
    resume_text TEXT,
    parsed_skills TEXT[],
    education JSONB,  -- {schools: [...], degrees: [...]}
    work_history JSONB  -- {companies: [...], titles: [...]}
);

-- Enhanced person data
CREATE TABLE people_discoveries (
    -- ... existing fields ...
    relevance_score FLOAT,  -- 0-1 overall relevance
    skill_match_score FLOAT,
    relationship_type TEXT,  -- 'alumni', '1st_degree', '2nd_degree', etc.
    mutual_connections INT,
    relevance_reasoning TEXT  -- Why this person is relevant
);
```

## 🔧 Implementation Plan

### Immediate Changes:

1. **orchestrator.py:**
   ```python
   def _initialize_sources(self):
       sources = {}
       # ONLY working sources
       sources['google_serp'] = GoogleSearchScraper()  # Primary
       sources['github'] = GitHubScraper()  # Secondary
       # apollo if configured
       sources['apollo'] = ApolloClient()  
       return sources
   ```

2. **Add source quality scores:**
   ```python
   SOURCE_QUALITY_SCORES = {
       'google_serp': 1.0,  # Highest quality
       'serpapi': 1.0,
       'apollo': 0.9,
       'github': 0.4,  # Low quality (minimal metadata)
   }
   ```

3. **Sort by quality + category:**
   - Primary sort: Source quality score
   - Secondary sort: Category (Recruiter > Manager > Senior > Peer)
   - Tertiary sort: Confidence score

4. **Enhanced OpenAI usage:**
   - Increase enhancement limit from 20 to 50 people
   - Use OpenAI to infer missing titles from GitHub bios
   - Extract location/department from bio text
   - Generate better categorization

### OpenAI Web Search Note:
- OpenAI API doesn't have native web search
- Could integrate with Perplexity API or Tavily API for AI-powered search
- For now, focus on enhancing existing SerpAPI data

## 📊 Expected Results After Changes

### Before:
- 30+ results, mixed quality
- GitHub results with no metadata cluttering top
- No clear prioritization

### After:
- **Tier 1:** SerpAPI results first (recruiters/managers with full LinkedIn profiles)
- **Tier 2:** GitHub results last (engineers, minimal info)
- Clear quality indicators
- Better categorization via OpenAI
- Production-ready for sharing

## 🚀 Future Enhancements (V2)

### When user/job context is available:

1. **Resume Parser Integration:**
   ```python
   def match_to_user_profile(person: Person, user_profile: UserProfile) -> float:
       alumni_match = check_alumni_connection(person, user_profile)
       company_match = check_shared_companies(person, user_profile)
       skill_overlap = calculate_skill_similarity(person.skills, user_profile.skills)
       
       return (alumni_match * 0.4 + company_match * 0.3 + skill_overlap * 0.3)
   ```

2. **Job Description Parser:**
   ```python
   def match_to_job_requirements(person: Person, job: JobContext) -> float:
       required_skills = extract_skills_from_jd(job.description)
       person_skills = person.skills or infer_skills_from_title(person.title)
       
       skill_match = len(set(required_skills) & set(person_skills)) / len(required_skills)
       title_relevance = calculate_title_similarity(person.title, job.title)
       
       return (skill_match * 0.6 + title_relevance * 0.4)
   ```

3. **LinkedIn API Integration (Paid):**
   - Get 1st/2nd degree connections
   - Mutual connection counts
   - Actual relationship graph

## 📋 Implementation Checklist

- [ ] Disable all broken scrapers
- [ ] Keep only SerpAPI + GitHub + Apollo
- [ ] Add source quality scoring
- [ ] Sort results by: quality → category → confidence
- [ ] Enhance OpenAI integration (50 people limit)
- [ ] Add better UI indicators for source quality
- [ ] Test with multiple companies
- [ ] Document limitations clearly
- [ ] Add "Future V2" section in UI about relevance matching

## 💡 Key Insight

**Current limitation:** We're finding relevant COMPANIES' people, but not filtering for YOUR relevance.

**Why this is OK for V1:**
- Users can manually filter the list
- Having 30-100 connections is better than 0
- Quality sorting helps (recruiters/managers first)

**V2 will add:**
- "This person went to your school ⭐"
- "You both worked at Company X 🔗"
- "Skills match: 85% ✅"
- "2nd degree connection via John Doe 👥"


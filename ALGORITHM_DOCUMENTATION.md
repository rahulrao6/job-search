# Algorithm Documentation & Improvement Guide

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Search Flow Diagram](#search-flow-diagram)
3. [Core Algorithms](#core-algorithms)
4. [Data Sources & Search Strategies](#data-sources--search-strategies)
5. [False Positive Sources & Solutions](#false-positive-sources--solutions)
6. [Improvement Opportunities](#improvement-opportunities)
7. [Frontend/Backend Integration Points](#frontendbackend-integration-points)

---

## System Architecture Overview

### High-Level Flow

```
Frontend Request
    ↓
API Route (/api/v1/search)
    ↓
ConnectionFinder.find_connections_with_context()
    ↓
[Phase 1: Free Sources] → ActuallyWorkingFreeSources
    ├─ Google Custom Search Engine
    ├─ Bing Web Search API (deprecated)
    └─ GitHub API
    ↓
PeopleAggregator (deduplicates)
    ↓
PersonValidator (filters false positives)
    ↓
OpenAI Enhancer (optional - enriches data)
    ↓
PersonCategorizer (categorizes: manager, recruiter, senior, peer)
    ↓
ProfileMatcher (calculates relevance scores)
    ↓
DiscoveryService (saves to database)
    ↓
Response to Frontend
```

### Key Components

1. **ConnectionFinder** (`src/core/orchestrator.py`)
   - Main orchestrator that coordinates all sources
   - Manages source quality scores
   - Handles caching and timeout management

2. **ActuallyWorkingFreeSources** (`src/scrapers/actually_working_free_sources.py`)
   - Primary search implementation
   - Integrates Google CSE, Bing, GitHub APIs

3. **PeopleAggregator** (`src/core/aggregator.py`)
   - Deduplicates results from multiple sources
   - Merges data from duplicate entries

4. **PersonValidator** (`src/utils/person_validator.py`)
   - Filters false positives
   - Validates person data quality

5. **PersonCategorizer** (`src/core/categorizer.py`)
   - Categorizes people into: Manager, Recruiter, Senior, Peer, Unknown

6. **ProfileMatcher** (`src/services/profile_matcher.py`)
   - Calculates relevance scores based on profile/job context
   - Identifies match reasons (alumni, ex-company, skills, etc.)

7. **DiscoveryService** (`src/services/discovery_service.py`)
   - Saves discoveries to database
   - Manages discovery retrieval

---

## Search Flow Diagram

### Detailed Search Process

```
1. REQUEST RECEIVED
   ├─ Company: "Stripe"
   ├─ Title: "Software Engineer"
   ├─ User Profile: {schools: ["MIT"], past_companies: ["Google"], skills: ["Python"]}
   └─ Job Context: {department: "Engineering", location: "SF", required_skills: ["Go", "Python"]}

2. QUERY BUILDING (ActuallyWorkingFreeSources._build_google_query_variations)
   ├─ Query 1: site:linkedin.com/in/ Stripe Software Engineer
   ├─ Query 2: site:linkedin.com/in/ Stripe Software Engineer Python Go
   ├─ Query 3: site:linkedin.com/in/ Stripe Software Engineer "MIT" (alumni search)
   ├─ Query 4: site:linkedin.com/in/ Stripe "Engineering" Software Engineer
   └─ Query 5: site:linkedin.com/in/ Stripe (fallback)

3. SOURCE EXECUTION
   ├─ Google CSE API
   │  ├─ Execute queries 1-5
   │  ├─ Parse LinkedIn URLs from results
   │  └─ Extract: name, title, LinkedIn URL
   ├─ Bing API (if configured, deprecated)
   └─ GitHub API
      ├─ Search: "Stripe Engineer in:bio type:user"
      └─ Extract: GitHub username, profile URL

4. AGGREGATION (PeopleAggregator)
   ├─ Deduplicate by (name_lowercase, company_lowercase)
   ├─ Merge data from multiple sources
   └─ Boost confidence for multi-source matches

5. VALIDATION (PersonValidator)
   ├─ Check: Name matches company? → FILTER
   ├─ Check: Past employee? (title contains "former", "ex-") → FILTER
   ├─ Check: Spam profile? (no LinkedIn, generic title) → FILTER
   ├─ Check: Missing critical info? → FILTER
   └─ Check: Company mismatch in title? → FILTER

6. ENHANCEMENT (OpenAI Enhancer - optional)
   ├─ Enrich person data with OpenAI
   ├─ Extract: department, location, skills, etc.
   └─ Limit: 10-20 people (time-based)

7. CATEGORIZATION (PersonCategorizer)
   ├─ Check: Contains recruiter keywords? → RECRUITER
   ├─ Check: Contains manager keywords? → MANAGER
   ├─ Check: Contains senior keywords? → SENIOR
   ├─ Check: Similar to target title? → PEER
   └─ Default: → UNKNOWN

8. RELEVANCE SCORING (ProfileMatcher)
   ├─ Base score: confidence_score (0.0-1.0)
   ├─ Alumni match? +0.3
   ├─ Ex-company match? +0.25
   ├─ Skills overlap? +0.2 (weighted by required/nice-to-have)
   ├─ Department match? +0.15
   ├─ Location match? +0.1
   └─ Source quality boost: +0.05 max
   └─ Cap at 1.0

9. SAVING (DiscoveryService)
   ├─ Convert Person → PersonDiscovery
   ├─ Include: relevance_score, match_reasons
   └─ Save to database

10. RESPONSE FORMATTING
    ├─ Group by category
    ├─ Sort by relevance_score (descending)
    └─ Return to frontend
```

---

## Core Algorithms

### 1. Query Building Algorithm

**Location**: `src/scrapers/actually_working_free_sources.py::_build_google_query_variations()`

**How it works**:
1. Builds base query: `site:linkedin.com/in/ {company}`
2. Creates variations based on available context:
   - **Primary**: Company + Title + Skills (if available)
   - **Alumni**: Company + Title + School (if user profile has schools)
   - **Department**: Company + Department + Title (if job context has department)
   - **Fallback**: Just Company + Title

**Current Issues**:
- ✅ Works well for basic searches
- ❌ **No semantic understanding** - exact string matching only
- ❌ **Limited query variations** - only 5 variations max
- ❌ **No query performance tracking** - doesn't learn which queries work best

**Improvement Opportunities**:
- Add semantic query expansion (synonyms, related terms)
- Track query performance and prioritize successful patterns
- Add negative keywords to exclude false positives
- Use job description to extract more relevant terms

---

### 2. Deduplication Algorithm

**Location**: `src/core/aggregator.py::_make_key()`

**How it works**:
1. Creates deduplication key: `(name.lower().strip(), company.lower().strip())`
2. If key exists, merges data:
   - Prefers non-null values
   - Merges skills lists
   - Boosts confidence (+0.2)
   - Tracks all sources

**Current Issues**:
- ✅ Simple and fast
- ❌ **Fails on name variations**: "John Smith" vs "John A. Smith" treated as different
- ❌ **Fails on company variations**: "Google" vs "Google LLC" vs "Alphabet" treated as different
- ❌ **No fuzzy matching** - exact match required

**Improvement Opportunities**:
- Use fuzzy string matching (Levenshtein distance)
- Normalize company names (handle LLC, Inc, etc.)
- Use LinkedIn URL as primary key (more reliable)
- Implement nickname/alias matching

---

### 3. False Positive Filtering Algorithm

**Location**: `src/utils/person_validator.py::validate_person()`

**How it works**:
Checks 5 validation rules:
1. **Name matches company**: Person named "Amazon" when searching Amazon → FILTER
2. **Past employee**: Title contains "former", "ex-", "previously at" → FILTER
3. **Spam profile**: Generic titles, no LinkedIn → FILTER
4. **Missing critical info**: No LinkedIn AND no meaningful title → FILTER
5. **Company mismatch**: Title mentions different company explicitly → FILTER

**Current Issues**:
- ✅ Filters obvious false positives
- ❌ **Too permissive on name matching** - only checks if company words appear in name
- ❌ **Limited past employment detection** - keyword-based only
- ❌ **No verification of current employment** - assumes LinkedIn profiles are current
- ❌ **GitHub profiles pass through** - marked as low quality but still included

**Improvement Opportunities**:
- Add LinkedIn profile parsing to verify current company
- Implement more sophisticated name-company matching (check if it's actually a name)
- Add employment date parsing (if available)
- Use LinkedIn "Current" vs "Past" indicators
- Add confidence thresholds per source type

---

### 4. Categorization Algorithm

**Location**: `src/core/categorizer.py::categorize()`

**How it works**:
1. Checks title for keywords in order:
   - **Recruiter keywords**: "recruiter", "talent", "hiring" → RECRUITER
   - **Manager keywords**: "manager", "director", "vp", "head of" → MANAGER
   - **Senior keywords**: "senior", "staff", "principal" → SENIOR (if target not already senior)
   - **Peer match**: Compares normalized titles (removes seniority keywords) → PEER
   - **Default**: → UNKNOWN

**Current Issues**:
- ✅ Covers most common cases
- ❌ **Keyword-based only** - no semantic understanding
- ❌ **Peer matching is simplistic** - just string comparison after removing seniority words
- ❌ **No handling of title variations**: "SWE" vs "Software Engineer"
- ❌ **Doesn't consider company hierarchy** - "Senior Manager" might still be peer-level

**Improvement Opportunities**:
- Use ML/NLP model for title classification
- Build title similarity model (embeddings)
- Consider job levels/bands if available
- Add industry-specific title mappings

---

### 5. Relevance Scoring Algorithm

**Location**: `src/services/profile_matcher.py::calculate_relevance()`

**How it works**:
1. Starts with base confidence score (0.5 default)
2. Adds weighted scores:
   - **Alumni match**: +0.3 (if school found in person's metadata)
   - **Ex-company match**: +0.25 (if person works at company user used to work at)
   - **Skills overlap**: +0.2 (weighted by required/nice-to-have/profile skills)
   - **Department match**: +0.15
   - **Location match**: +0.1
   - **Source quality boost**: +0.05 max
3. Caps at 1.0

**Current Issues**:
- ✅ Good coverage of matching criteria
- ❌ **Alumni matching is weak** - only checks if school keywords appear in text
- ❌ **Skills matching is basic** - only exact/fuzzy string matching
- ❌ **No temporal relevance** - doesn't consider how recent the connection is
- ❌ **No mutual connection scoring** - doesn't check if person has connections in common

**Improvement Opportunities**:
- Parse LinkedIn profiles to extract actual education history
- Use semantic similarity for skills (e.g., "ML" ≈ "Machine Learning")
- Add recency weighting (recent posts, recent job changes)
- Integrate LinkedIn connection graph if available
- Add geographic proximity scoring

---

## Data Sources & Search Strategies

### Google Custom Search Engine (Primary Source)

**Quality Score**: 0.9 (high)

**How it works**:
1. Uses Google Custom Search Engine API
2. Queries: `site:linkedin.com/in/ {company} {title}`
3. Parses results to extract:
   - Name (from title: "Name - Title - LinkedIn")
   - Title (from title or snippet)
   - LinkedIn URL

**Strengths**:
- ✅ Returns actual LinkedIn profiles
- ✅ High-quality results
- ✅ Free tier: 100 searches/day

**Weaknesses**:
- ❌ Limited to 100/day (can upgrade)
- ❌ Results depend on Google's indexing
- ❌ May miss recent profiles not yet indexed

**False Positive Sources**:
- Past employees (if their LinkedIn still shows the company)
- People who mention the company in bio but don't work there
- Generic LinkedIn profiles that mention company name

---

### Bing Web Search API (Deprecated)

**Quality Score**: 0.85 (high)

**Status**: DEPRECATED - kept for backward compatibility

**Issues**:
- Similar to Google CSE but with different indexing
- Not actively maintained

---

### GitHub API (Low Quality, Enrichment Only)

**Quality Score**: 0.2 (low)

**How it works**:
1. Searches GitHub users by company in bio
2. Query: `{company} {title} in:bio type:user`
3. Returns GitHub usernames only

**Strengths**:
- ✅ Free and unlimited (with token: 5000/hour)
- ✅ Can find developers not on LinkedIn

**Weaknesses**:
- ❌ No professional titles (just usernames)
- ❌ No LinkedIn URLs
- ❌ Many false positives (anyone can put company in bio)
- ❌ No verification of actual employment

**False Positive Sources**:
- Developers who put company name in bio but don't work there
- Open source contributors
- People who list company as "interested in working at"

**Recommendation**: 
- Keep for enrichment but heavily deprioritize
- Consider filtering out unless we can verify employment

---

### Company Website Scraping (Not Currently Used)

**Quality Score**: 0.6 (medium)

**Status**: Skipped for speed

**How it would work**:
1. Scrape company team/about pages
2. Extract employee names and titles
3. Search LinkedIn for matches

**Strengths**:
- ✅ High accuracy (current employees only)
- ✅ Free

**Weaknesses**:
- ❌ Slow (adds ~5 seconds per company)
- ❌ Many companies don't have team pages
- ❌ Format varies by company

---

## False Positive Sources & Solutions

### Problem 1: Past Employees Appearing as Current

**Why it happens**:
- LinkedIn profiles still show past company in search results
- Google indexes historical LinkedIn data
- People mention company in bio even after leaving

**Current filtering**:
- ✅ Checks for keywords: "former", "ex-", "previously at"
- ❌ Doesn't parse LinkedIn date ranges
- ❌ Doesn't verify current employment

**Improvements needed**:
1. Parse LinkedIn profiles to extract employment dates
2. Check if person's "Current" role is at target company
3. Use LinkedIn API if available (requires premium)
4. Cross-reference with company website team pages

**Priority**: HIGH (major source of false positives)

---

### Problem 2: Name Matches Company Name

**Why it happens**:
- Person named "Amazon" when searching for Amazon
- Person named "Meta" when searching for Meta
- Rare but annoying edge case

**Current filtering**:
- ✅ Checks if company name appears in person's name
- ❌ Too permissive (might filter valid names like "Amazonia")
- ❌ Doesn't check if name is actually a valid name

**Improvements needed**:
1. Use name validation library to check if it's a real name
2. Check if name is common word vs proper name
3. Only filter if exact match (not substring)

**Priority**: MEDIUM (rare but easy fix)

---

### Problem 3: Generic/Spam Profiles

**Why it happens**:
- LinkedIn allows generic titles
- Some profiles have minimal information
- Scrapers return any LinkedIn profile matching query

**Current filtering**:
- ✅ Checks for spam indicators in title
- ✅ Requires LinkedIn URL or meaningful title
- ❌ Doesn't verify profile quality

**Improvements needed**:
1. Check profile completeness (connections, endorsements)
2. Verify profile has professional photo
3. Check for activity/engagement indicators
4. Filter profiles with generic titles

**Priority**: MEDIUM

---

### Problem 4: GitHub False Positives

**Why it happens**:
- Anyone can put company name in GitHub bio
- No verification of employment
- Many developers list companies they're interested in, not employed by

**Current filtering**:
- ✅ Deprioritized (quality score 0.2)
- ✅ Requires additional info
- ❌ Still included in results

**Improvements needed**:
1. Only include if we can verify employment (LinkedIn cross-reference)
2. Filter if company name appears but no other employment indicators
3. Consider removing GitHub source entirely for production

**Priority**: HIGH (low-quality results polluting results)

---

### Problem 5: Weak Alumni Matching

**Why it happens**:
- Alumni matching only checks if school keywords appear in text
- LinkedIn profiles may not explicitly mention school in searchable text
- Education section may not be indexed by Google

**Current matching**:
- Checks title, location, department, skills for school keywords
- Very basic string matching

**Improvements needed**:
1. Parse LinkedIn profiles to extract actual education history
2. Use LinkedIn API to get education data
3. Build school aliases/normalizations database
4. Match on graduation years if available

**Priority**: MEDIUM (would improve relevance scores significantly)

---

### Problem 6: Skills Matching Too Basic

**Why it happens**:
- Only exact/fuzzy string matching
- Doesn't understand synonyms ("ML" vs "Machine Learning")
- Doesn't consider skill levels

**Current matching**:
- Exact matches: "Python" = "Python"
- Fuzzy matches: uses synonym dictionary (limited)
- No semantic understanding

**Improvements needed**:
1. Use skill taxonomy/synonyms database
2. Implement semantic similarity (embeddings)
3. Consider skill proficiency levels
4. Weight by skill importance in job description

**Priority**: MEDIUM (would improve relevance scores)

---

## Improvement Opportunities

### Short-Term Improvements (Easy Wins)

1. **Better Name-Company Validation**
   - Use name validation library
   - Only filter exact matches, not substrings
   - Check if it's a common word vs proper name

2. **Enhanced Past Employee Detection**
   - Parse LinkedIn employment dates
   - Check for "Current" vs "Past" indicators
   - More keyword variations

3. **GitHub Source Filtering**
   - Only include if LinkedIn cross-reference exists
   - Filter profiles with company name but no employment indicators
   - Consider removing entirely

4. **Query Performance Tracking**
   - Log which queries return best results
   - Prioritize successful query patterns
   - A/B test query variations

5. **Company Name Normalization**
   - Handle LLC, Inc, variations
   - Map parent companies (Facebook → Meta)
   - Improve deduplication accuracy

---

### Medium-Term Improvements (Requires Development)

1. **LinkedIn Profile Parsing**
   - Parse actual LinkedIn profiles (not just search results)
   - Extract: current employment, education, skills
   - Verify employment status

2. **Semantic Skills Matching**
   - Build skill taxonomy
   - Use embeddings for similarity
   - Handle synonyms automatically

3. **Better Categorization**
   - Use ML model for title classification
   - Title similarity embeddings
   - Industry-specific mappings

4. **Improved Deduplication**
   - Fuzzy string matching
   - LinkedIn URL as primary key
   - Nickname/alias matching

5. **Alumni Matching Enhancement**
   - Parse LinkedIn education sections
   - School aliases database
   - Graduation year matching

---

### Long-Term Improvements (Requires Infrastructure)

1. **LinkedIn API Integration**
   - Official LinkedIn API access
   - Real-time employment verification
   - Connection graph data

2. **ML-Based Relevance Scoring**
   - Train model on user feedback
   - Personalize scoring per user
   - Learn from successful connections

3. **Real-Time Employment Verification**
   - Webhook integration with employment databases
   - Periodic verification of saved discoveries
   - Automatic false positive removal

4. **Advanced Search Strategies**
   - Multi-query ensemble
   - Query expansion with synonyms
   - Negative keyword filtering

5. **User Feedback Loop**
   - Track which connections are contacted
   - Learn which results lead to successful connections
   - Continuously improve algorithms

---

## Frontend/Backend Integration Points

### API Endpoints

#### `/api/v1/search` (POST)

**Request**:
```json
{
  "company": "Stripe",
  "job_title": "Software Engineer",
  "profile": {
    "schools": ["MIT"],
    "past_companies": ["Google"],
    "skills": ["Python", "Go"]
  },
  "job_context": {
    "department": "Engineering",
    "location": "San Francisco",
    "required_skills": ["Go", "Python"],
    "nice_to_have_skills": ["Kubernetes"]
  },
  "filters": {
    "categories": ["recruiter", "manager"],
    "min_confidence": 0.7,
    "min_relevance": 0.6
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "results": {
      "by_category": {
        "recruiter": [
          {
            "name": "Jane Doe",
            "title": "Technical Recruiter",
            "company": "Stripe",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "relevance_score": 0.85,
            "match_reasons": ["alumni_match (MIT)", "skills_match (2 skills)"],
            "confidence": 0.9,
            "source": "google_cse"
          }
        ],
        "manager": [...],
        "peer": [...]
      },
      "category_counts": {
        "recruiter": 5,
        "manager": 3,
        "peer": 12
      },
      "insights": {
        "alumni_matches": 8,
        "ex_company_matches": 2,
        "skills_matches": 15
      }
    },
    "quota": {
      "searches_remaining": 45,
      "daily_limit": 50
    }
  }
}
```

---

### Data Flow

1. **Frontend → Backend**
   - User submits search with profile/resume
   - Backend parses resume (if uploaded)
   - Backend extracts profile data

2. **Backend Processing**
   - Search sources
   - Filter false positives
   - Calculate relevance scores
   - Save to database

3. **Backend → Frontend**
   - Return categorized results
   - Include relevance scores and match reasons
   - Provide insights (alumni matches, etc.)

4. **Frontend Display**
   - Group by category
   - Sort by relevance score
   - Show match reasons
   - Allow filtering

---

### Database Schema

**Table: `people_discoveries`**
- `id`: UUID
- `job_id`: UUID (foreign key)
- `user_id`: UUID (foreign key)
- `full_name`: string
- `title`: string
- `company`: string
- `linkedin_url`: string
- `relevance_score`: float (0.0-1.0)
- `match_reasons`: array of strings
- `person_type`: enum (recruiter, manager, senior, peer, unknown)
- `source`: string
- `confidence_score`: float
- `contacted`: boolean
- `created_at`: timestamp

---

### Key Integration Points

1. **Profile Extraction** (`src/extractors/resume_parser.py`)
   - Parses resume to extract: schools, companies, skills
   - Used to build search queries and calculate relevance

2. **Job Context** (`src/models/job_context.py`)
   - Stores job description, company, department, location
   - Used for targeted searches and matching

3. **Relevance Scoring** (`src/services/profile_matcher.py`)
   - Calculates how relevant each person is
   - Returns score + match reasons
   - Frontend can use this to prioritize display

4. **Discovery Storage** (`src/services/discovery_service.py`)
   - Saves results for later retrieval
   - Allows marking as "contacted"
   - Tracks user interactions

---

### Frontend Recommendations

1. **Display Relevance Scores**
   - Show score prominently
   - Use color coding (green = high, yellow = medium, red = low)
   - Allow sorting by relevance

2. **Show Match Reasons**
   - Display why person is relevant
   - Highlight: "Alumni (MIT)", "Ex-company (Google)", "Skills match (3 skills)"

3. **Filter Options**
   - By category (recruiter, manager, etc.)
   - By min relevance score
   - By match type (alumni, ex-company, skills)

4. **Feedback Loop**
   - Allow marking as "contacted"
   - Allow marking as "not relevant" (false positive)
   - Use feedback to improve algorithms

5. **Insights Dashboard**
   - Show stats: "8 alumni matches", "2 ex-company matches"
   - Highlight best categories
   - Suggest which connections to prioritize

---

## Summary

### Current Strengths
- ✅ Multi-source aggregation works well
- ✅ Good categorization coverage
- ✅ Relevance scoring considers multiple factors
- ✅ Basic false positive filtering

### Current Weaknesses
- ❌ False positives from past employees
- ❌ Weak alumni matching (keyword-based only)
- ❌ Basic skills matching (no semantic understanding)
- ❌ GitHub source adds low-quality results
- ❌ No employment verification

### Priority Improvements
1. **HIGH**: Better past employee detection (LinkedIn parsing)
2. **HIGH**: Filter/remove GitHub source or heavily restrict
3. **MEDIUM**: Enhanced alumni matching (parse LinkedIn education)
4. **MEDIUM**: Semantic skills matching
5. **MEDIUM**: Improved deduplication (fuzzy matching)

### Next Steps
1. Implement LinkedIn profile parsing for employment verification
2. Add query performance tracking
3. Improve deduplication with fuzzy matching
4. Remove or heavily filter GitHub results
5. Build user feedback loop

---

*Last Updated: 2025-11-02*
*Version: 1.0*


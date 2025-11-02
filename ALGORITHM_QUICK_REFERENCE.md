# Algorithm Quick Reference Guide

## 🔍 Search Flow (30-second overview)

```
Request → Query Building → Source Search → Aggregation → Validation → 
Categorization → Relevance Scoring → Save → Response
```

## 📊 Component Responsibilities

| Component | Purpose | Key File |
|-----------|---------|----------|
| **ConnectionFinder** | Orchestrates entire search | `src/core/orchestrator.py` |
| **ActuallyWorkingFreeSources** | Executes searches | `src/scrapers/actually_working_free_sources.py` |
| **PeopleAggregator** | Deduplicates results | `src/core/aggregator.py` |
| **PersonValidator** | Filters false positives | `src/utils/person_validator.py` |
| **PersonCategorizer** | Categorizes people | `src/core/categorizer.py` |
| **ProfileMatcher** | Calculates relevance | `src/services/profile_matcher.py` |
| **DiscoveryService** | Saves to database | `src/services/discovery_service.py` |

## 🔎 How Searches Work

### Query Building
- **Base**: `site:linkedin.com/in/ {company} {title}`
- **Variations**: Add skills, schools, department
- **Max variations**: 5 queries

### Sources Executed
1. **Google CSE** (Quality: 0.9) - Primary, returns LinkedIn profiles
2. **Bing API** (Quality: 0.85) - Deprecated
3. **GitHub API** (Quality: 0.2) - Low quality, usernames only

### Deduplication
- **Key**: `(name.lower(), company.lower())`
- **Issue**: Fails on name/company variations

### Validation Rules
1. ❌ Name matches company name
2. ❌ Title contains "former", "ex-", "previously at"
3. ❌ Spam profile (generic title, no LinkedIn)
4. ❌ Missing critical info (no LinkedIn AND no title)
5. ❌ Title mentions different company

### Categorization
1. **Recruiter**: Contains "recruiter", "talent", "hiring"
2. **Manager**: Contains "manager", "director", "vp", "head of"
3. **Senior**: Contains "senior", "staff", "principal" (if target not senior)
4. **Peer**: Title similar to target (after removing seniority words)
5. **Unknown**: Default

### Relevance Scoring
- **Base**: confidence_score (0.5 default)
- **Alumni match**: +0.3
- **Ex-company match**: +0.25
- **Skills overlap**: +0.2 (weighted)
- **Department match**: +0.15
- **Location match**: +0.1
- **Source quality**: +0.05 max
- **Cap**: 1.0

## 🐛 False Positive Sources

| Issue | Why It Happens | Current Fix | Needs Improvement |
|-------|---------------|-------------|-------------------|
| **Past Employees** | LinkedIn shows historical data | Keyword check ("former") | Parse LinkedIn dates |
| **Name = Company** | Person named "Amazon" | Name contains company words | Too permissive |
| **GitHub False Positives** | Anyone can put company in bio | Low quality score | Consider removing |
| **Weak Alumni Match** | Keyword-based only | Text search for school | Parse LinkedIn education |
| **Generic Skills Match** | String matching only | Synonym dictionary (limited) | Semantic similarity |

## 🎯 Improvement Priorities

### HIGH Priority
1. ✅ **Better Past Employee Detection**
   - Parse LinkedIn employment dates
   - Check "Current" vs "Past" indicators
   - File: `src/utils/person_validator.py`

2. ✅ **GitHub Source Filtering**
   - Only include if LinkedIn cross-reference
   - Or remove entirely
   - File: `src/scrapers/actually_working_free_sources.py`

### MEDIUM Priority
3. ✅ **Enhanced Alumni Matching**
   - Parse LinkedIn education sections
   - File: `src/services/profile_matcher.py` (line 71-93)

4. ✅ **Semantic Skills Matching**
   - Build skill taxonomy
   - Use embeddings
   - File: `src/services/profile_matcher.py` (line 107-167)

5. ✅ **Improved Deduplication**
   - Fuzzy string matching
   - LinkedIn URL as primary key
   - File: `src/core/aggregator.py` (line 64-69)

### LOW Priority
6. Better name-company validation
7. Query performance tracking
8. Company name normalization

## 🔧 Quick Fixes

### Fix 1: Remove GitHub from Results
**File**: `src/core/orchestrator.py`
**Line**: ~186
**Change**: Filter out GitHub results before categorization

```python
# After aggregation, before validation
quality_people = [p for p in all_people 
                  if p.source not in ['github', 'github_legacy']]
```

### Fix 2: Better Past Employee Detection
**File**: `src/utils/person_validator.py`
**Line**: ~122
**Add**: Check for date ranges in title

```python
# In _is_past_employee()
if re.search(r'\d{4}\s*-\s*\d{4}', title_lower):
    return True  # Has date range, likely past
```

### Fix 3: Improved Name Validation
**File**: `src/utils/person_validator.py`
**Line**: ~101
**Change**: Only filter exact matches

```python
# In _name_matches_company()
# Only filter if exact word match
name_words = set(name_lower.split())
if self.company_words & name_words and len(self.company_words) == 1:
    return True  # Only if single word company name
```

## 📈 Metrics to Track

1. **False Positive Rate**: % of results marked as "not relevant"
2. **Query Success Rate**: % of queries returning results
3. **Source Quality**: Average relevance score by source
4. **Category Distribution**: Recruiter vs Manager vs Peer
5. **Match Type Distribution**: Alumni vs Ex-company vs Skills

## 🔗 Key Integration Points

- **API Route**: `src/api/routes.py::search()` (line 68)
- **Search Entry**: `src/core/orchestrator.py::find_connections_with_context()` (line 302)
- **Profile Matching**: `src/services/profile_matcher.py::calculate_relevance()` (line 20)
- **Response Format**: `src/api/schemas.py::format_search_response()` (line 114)

## 📝 Notes for Frontend

- **Relevance scores** are 0.0-1.0, higher is better
- **Match reasons** explain why person is relevant
- **Categories** can be used for filtering
- **Source** indicates data quality (google_cse = high, github = low)
- **Confidence** is data completeness, not relevance

---

*See ALGORITHM_DOCUMENTATION.md for full details*


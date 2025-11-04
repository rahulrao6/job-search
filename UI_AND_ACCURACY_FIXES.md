# UI and Accuracy Fixes - November 3, 2025

## Problem Summary
1. **UI Issue**: Only showing managers, not all categories (missing 'unknown' category)
2. **Accuracy Issue**: Getting wrong companies (e.g., "Rootwords" instead of "Root")

## Changes Made

### 1. UI Display Fix ✅
**File**: `web_app.py`
- Added 'unknown' to the category order array
- Added emoji (❓) and color (#6b7280) for 'unknown' category
- Updated category summary section to properly display unknown results

**Before**:
```javascript
const categoryOrder = ['recruiter', 'manager', 'senior', 'peer'];
```

**After**:
```javascript
const categoryOrder = ['recruiter', 'manager', 'senior', 'peer', 'unknown'];
```

### 2. Company Verification Improvements ✅
**File**: `src/scrapers/actually_working_free_sources.py`

#### a. Enhanced False Positive Detection
- Added "rootwords" and other similar companies to the false positive list
- Now handles both "root" and "root.io" variations

```python
false_positive_companies = {
    'root': ['root insurance', 'roots ai', 'square root', 'grassroots', 'root cause', 
            'rootwords', 'root capital', 'root ventures', 'root health', 'root analytics'],
    'root.io': [...same list...],
}
```

#### b. Improved Company Name Matching
- Now accepts both "Root" and "Root.io" as valid matches
- Handles LinkedIn URL patterns with variations (/company/root/, /company/root-io/)
- Checks multiple company name variations in employment patterns

#### c. Smarter Search Queries
- When searching for "Root.io", also searches for just "Root"
- Prioritizes domain-based searches when available
- Generates variations to catch more valid profiles

## How It Works Now

1. **Search Query Generation**:
   - Primary: `site:linkedin.com/in/ "Root" "root.io" AI Engineer`
   - Fallback: `site:linkedin.com/in/ "Root" AI Engineer`
   
2. **Company Verification**:
   - ✅ Accepts: "at Root", "@ Root.io", "/company/root", etc.
   - ❌ Rejects: "Rootwords", "Root Insurance", "Roots AI", etc.
   
3. **UI Display**:
   - Shows all categories: Recruiters, Managers, Senior, Peer, **and Unknown**
   - Unknown results appear at the bottom with ❓ icon

## Testing Instructions

1. Visit http://localhost:8000/api-test
2. Search for: 
   - Company: `Root` or `Root.io` 
   - Job Title: `AI Engineer`
   - Job URL: `https://builtin.com/job/ai-engineer/7205920`

You should now see:
- All categories displayed (including unknown)
- Better accuracy (no more Rootwords, Root Insurance, etc.)
- People who work at Root (whether their profile says "Root" or "Root.io")

## Next Steps

If results still need improvement:
1. Add more company-specific false positives as discovered
2. Consider using OpenAI to verify company matches in edge cases
3. Implement stricter validation for high-ambiguity company names

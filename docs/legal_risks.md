# Legal & Terms of Service Considerations

## Overview

This document outlines the legal implications and Terms of Service (ToS) considerations for each data source.

⚠️ **Important**: Web scraping exists in a legal gray area. This tool is for educational and research purposes. Use responsibly.

## Summary Table

| Source | Legal Risk | ToS Compliance | Recommended? |
|--------|-----------|----------------|--------------|
| Apollo.io API | ✅ None | ✅ Compliant | YES |
| Company websites | ✅ Low | ✅ Generally OK | YES |
| GitHub public data | ✅ Low | ✅ Within limits | YES |
| Crunchbase free | ✅ Low | ⚠️ Gray area | YES |
| Google SERP | ⚠️ Medium | ⚠️ Against ToS | Use API |
| LinkedIn scraping | ⚠️ High | ❌ Violates ToS | NO (risky) |

## Detailed Breakdown

### ✅ LOW RISK - Recommended

#### Apollo.io API
- **Legal Status**: ✅ Legal - using official API
- **ToS Compliance**: ✅ Fully compliant
- **Data Rights**: Apollo has rights to share this data
- **Risk Level**: None
- **Recommendation**: **Use freely** - this is the safest option

#### Company Career/Team Pages
- **Legal Status**: ✅ Legal - public information
- **ToS Compliance**: ✅ Generally compliant (check individual site ToS)
- **Risk Level**: Very low
- **Best Practices**:
  - Respect robots.txt
  - Don't overload servers (rate limit)
  - Only scrape public pages
- **Recommendation**: **Safe to use**

#### GitHub Public Profiles
- **Legal Status**: ✅ Legal - public data
- **ToS Compliance**: ✅ Compliant for reasonable use
- **GitHub ToS**: Allows scraping public data with rate limits
- **Risk Level**: Low
- **Best Practices**:
  - Use official API when possible
  - Respect rate limits (5000/hour with auth)
  - Don't scrape private repos
- **Recommendation**: **Safe to use**

#### Crunchbase
- **Legal Status**: ⚠️ Gray area
- **ToS Compliance**: ⚠️ ToS discourages scraping but data is public
- **Risk Level**: Low to medium
- **Best Practices**:
  - Light scraping only
  - Consider using official API for production
  - Cache results to minimize requests
- **Recommendation**: **OK for PoC**, consider API for production

### ⚠️ MEDIUM RISK - Use with Caution

#### Google SERP Scraping
- **Legal Status**: ⚠️ Gray area - public results but automated access
- **ToS Compliance**: ❌ Google ToS prohibits automated queries
- **Risk Level**: Medium
- **Consequences**: IP blocks, CAPTCHA challenges
- **Best Practices**:
  - Use official API (SerpAPI) instead
  - If scraping: rotate IPs, add delays
  - Don't make excessive requests
- **Recommendation**: **Use SerpAPI instead** (100 free searches/month)

#### Bing Search
- **Legal Status**: ⚠️ Similar to Google
- **ToS Compliance**: ❌ ToS prohibits automated access
- **Risk Level**: Medium
- **Best Practices**: Use Bing Search API (free tier available)
- **Recommendation**: **Use official API**

### ❌ HIGH RISK - Not Recommended

#### LinkedIn Scraping
- **Legal Status**: ⚠️ Legal gray area (hiQ vs LinkedIn case)
- **ToS Compliance**: ❌ **Directly violates LinkedIn ToS**
- **Risk Level**: **HIGH**
- **Consequences**:
  - Account permanent ban
  - IP blocks
  - Potential legal action for commercial use
  - CFAA violations (in US)
- **Recent Precedent**: 
  - hiQ Labs case: Scraping public data ruled legal
  - BUT: LinkedIn actively enforces ToS with bans
  - Using authenticated session = clear ToS violation
- **Recommendation**: **AVOID for production**
  - Use LinkedIn API (requires approval, paid)
  - Use third-party APIs (Proxycurl, Apollo) instead
  - Only use for personal research at your own risk

## Legal Frameworks

### United States
- **Computer Fraud and Abuse Act (CFAA)**: Accessing systems "without authorization"
  - Scraping public data: Generally OK (hiQ precedent)
  - Bypassing technical barriers: Risky
  - Using authenticated sessions: Potentially violates CFAA
- **Copyright**: Facts not copyrightable, but presentation might be
- **Contracts**: ToS violations can be breach of contract

### European Union
- **GDPR**: Personal data protection
  - Name, email, job title = personal data
  - Need legal basis to process
  - Research/legitimate interest may apply
- **Database Directive**: Protects substantial databases

## Best Practices

### 1. Prioritize Official APIs
- Apollo, SerpAPI, GitHub API = legally safe
- Pay for data when budget allows
- More reliable than scraping

### 2. Respect Rate Limits
- Even legal scraping can become illegal if it harms the site
- Our defaults are conservative
- Don't change limits aggressively

### 3. Add Value
- Don't republish scraped data as-is
- Transform data (categorization, matching)
- Personal use < Commercial use (risk levels)

### 4. Be Transparent
- Identify your bot in user agent
- Respect robots.txt
- Provide contact info in user agent

### 5. Cache Aggressively
- Don't re-scrape same data
- Default: 24hr cache
- Reduces load on sources

### 6. Have Fallbacks
- If source blocks you, respect it
- Don't try to evade blocks
- Use alternative sources

## Recommendations by Use Case

### Personal Job Search (You)
- **Use**: Apollo, company sites, GitHub, Google API
- **Avoid**: LinkedIn scraping (not worth account ban)
- **Risk**: Very low

### Research Project
- **Use**: All free sources + APIs
- **Document**: How you're collecting data
- **Consider**: IRB approval if publishing

### Commercial Product
- **Use**: ONLY official APIs (Apollo, LinkedIn API, etc.)
- **Avoid**: All scraping
- **Cost**: Budget for paid APIs
- **Get**: Legal review

### High-Volume Production
- **Required**: 
  - Legal counsel
  - Terms of service reviews
  - Official API agreements
  - Data processing agreements (GDPR)

## For This PoC

**Our Approach**:
1. ✅ Prioritize free APIs (Apollo, SerpAPI)
2. ✅ Scrape only public company pages
3. ✅ Respect rate limits
4. ⚠️ Include LinkedIn option but warn users
5. ✅ Cache everything
6. ✅ Provide opt-outs via config

**Your Risk Level**: LOW (if you skip LinkedIn scraping)

**Recommended Settings**:
```yaml
sources:
  apollo: enabled: true          # ✅ Safe
  company_pages: enabled: true   # ✅ Safe
  github: enabled: true          # ✅ Safe
  google_serp: enabled: true     # ✅ Safe with API
  linkedin_public: enabled: false # ❌ Skip unless you accept risk
```

## Disclaimer

This tool is provided for educational purposes. The authors are not responsible for misuse or legal consequences. Users are responsible for:
- Understanding applicable laws
- Reviewing ToS of each service
- Accepting risks of scraping
- Using responsibly

**When in doubt, use official APIs.**


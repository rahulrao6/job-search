# 🎨 Frontend Integration Guide

## How to Use the Improved API in Your Frontend

### 1. Basic Search Request

```javascript
// Simple search
const searchBasic = async () => {
  const response = await fetch('/api/v1/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      company: 'Root',
      job_title: 'AI Engineer'
    })
  });
  
  const data = await response.json();
  return data.connections;
};
```

### 2. Enhanced Search with Domain (Recommended)

```javascript
// Better accuracy with domain
const searchWithDomain = async (jobUrl) => {
  // First parse the job if URL provided
  let jobData = {};
  if (jobUrl) {
    const parseResponse = await fetch('/api/v1/job/parse', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ job_url: jobUrl })
    });
    
    jobData = await parseResponse.json();
  }
  
  // Search with extracted domain
  const response = await fetch('/api/v1/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      company: jobData.company || 'Root',
      job_title: jobData.job_title || 'AI Engineer',
      company_domain: jobData.company_domain || 'root.io',
      department: jobData.department,
      location: jobData.location,
      required_skills: jobData.required_skills
    })
  });
  
  return await response.json();
};
```

### 3. Filtering Results by Quality

```javascript
// Client-side quality filtering
const filterConnectionsByQuality = (connections) => {
  // Separate into quality tiers
  const tiers = {
    premium: [],      // Recruiters & Managers with high confidence
    high: [],         // Senior & Peers with high confidence
    medium: [],       // Any category with medium confidence
    review: []        // Unknown category or low confidence
  };
  
  connections.forEach(person => {
    // Check confidence (includes employment verification)
    const isHighConfidence = person.confidence >= 0.8;
    const isMediumConfidence = person.confidence >= 0.6;
    
    // Premium tier: Recruiters/Managers with verification
    if (['recruiter', 'manager'].includes(person.category) && isHighConfidence) {
      tiers.premium.push(person);
    }
    // High tier: Senior/Peers with good confidence
    else if (['senior', 'peer'].includes(person.category) && isHighConfidence) {
      tiers.high.push(person);
    }
    // Medium tier: Any known category with decent confidence
    else if (person.category !== 'unknown' && isMediumConfidence) {
      tiers.medium.push(person);
    }
    // Review tier: Unknown or low confidence
    else {
      tiers.review.push(person);
    }
  });
  
  return tiers;
};
```

### 4. Displaying Results with Quality Indicators

```jsx
// React component example
const ConnectionCard = ({ person }) => {
  // Determine quality indicators
  const isVerified = person.confidence >= 0.8;
  const hasLinkedIn = Boolean(person.linkedin_url);
  const isRelevantRole = person.category !== 'unknown';
  
  return (
    <div className={`connection-card ${person.category}`}>
      {/* Quality badges */}
      <div className="badges">
        {isVerified && <span className="badge verified">✓ Verified</span>}
        {hasLinkedIn && <span className="badge linkedin">LinkedIn</span>}
        {person.category === 'recruiter' && <span className="badge priority">🎯 Recruiter</span>}
        {person.category === 'manager' && <span className="badge priority">👔 Manager</span>}
      </div>
      
      {/* Person details */}
      <h3>{person.name}</h3>
      <p className="title">{person.title || 'Title not available'}</p>
      <p className="company">{person.company}</p>
      
      {/* Confidence indicator */}
      <div className="confidence">
        <div className="confidence-bar">
          <div 
            className="confidence-fill" 
            style={{width: `${person.confidence * 100}%`}}
          />
        </div>
        <span>{Math.round(person.confidence * 100)}% confidence</span>
      </div>
      
      {/* Actions */}
      <div className="actions">
        {hasLinkedIn && (
          <a href={person.linkedin_url} target="_blank" className="btn-linkedin">
            View LinkedIn
          </a>
        )}
        {person.email && (
          <button className="btn-email">Copy Email</button>
        )}
      </div>
    </div>
  );
};
```

### 5. Smart Result Ordering

```javascript
// Order results for best user experience
const orderResultsForDisplay = (connections) => {
  // Custom sorting that preserves API ranking but groups by category
  const categoryOrder = {
    'recruiter': 1,
    'manager': 2,
    'senior': 3,
    'peer': 4,
    'unknown': 5
  };
  
  return connections.sort((a, b) => {
    // First by category priority
    const categoryDiff = categoryOrder[a.category] - categoryOrder[b.category];
    if (categoryDiff !== 0) return categoryDiff;
    
    // Then by confidence (already includes verification)
    return b.confidence - a.confidence;
  });
};
```

### 6. Handling Unknown Results

```javascript
// Decide what to do with unknown category results
const handleUnknownResults = (connections) => {
  const unknown = connections.filter(c => c.category === 'unknown');
  
  if (unknown.length > 0) {
    // Option 1: Show with warning
    return {
      show: true,
      message: `${unknown.length} results need manual review`,
      cssClass: 'results-warning'
    };
    
    // Option 2: Hide but allow toggle
    return {
      show: false,
      allowToggle: true,
      toggleText: `Show ${unknown.length} uncertain results`
    };
    
    // Option 3: Queue for enrichment
    return {
      show: false,
      enrichmentQueue: unknown.map(u => u.id)
    };
  }
};
```

### 7. Full Integration Example

```javascript
class ConnectionFinder {
  constructor(apiToken) {
    this.token = apiToken;
    this.cache = new Map();
  }
  
  async findConnections(jobUrl, userProfile = {}) {
    // Check cache first
    const cacheKey = `${jobUrl}-${JSON.stringify(userProfile)}`;
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }
    
    try {
      // Step 1: Parse job for company info
      const jobData = await this.parseJob(jobUrl);
      
      // Step 2: Search with all available context
      const searchData = await this.search({
        company: jobData.company,
        job_title: jobData.job_title,
        company_domain: jobData.company_domain,  // KEY: Better accuracy
        department: jobData.department,
        location: jobData.location,
        required_skills: jobData.required_skills,
        // Include user profile for better matches
        ...userProfile
      });
      
      // Step 3: Process results
      const processed = {
        total: searchData.total_found,
        connections: this.processConnections(searchData.connections),
        insights: searchData.insights,
        quota: searchData.quota
      };
      
      // Cache results
      this.cache.set(cacheKey, processed);
      
      return processed;
      
    } catch (error) {
      console.error('Connection search failed:', error);
      throw error;
    }
  }
  
  processConnections(connections) {
    // Filter by quality tiers
    const tiers = this.filterByQuality(connections);
    
    // Only return high-quality results by default
    const highQuality = [
      ...tiers.premium,
      ...tiers.high,
      ...tiers.medium.filter(c => c.confidence >= 0.7)
    ];
    
    return {
      primary: highQuality,
      review: tiers.review,  // Available but not shown by default
      stats: {
        verified: highQuality.filter(c => c.confidence >= 0.8).length,
        recruiters: highQuality.filter(c => c.category === 'recruiter').length,
        managers: highQuality.filter(c => c.category === 'manager').length
      }
    };
  }
}

// Usage
const finder = new ConnectionFinder(authToken);
const results = await finder.findConnections(
  'https://builtin.com/job/ai-engineer/7205920',
  {
    skills: ['Python', 'Machine Learning'],
    schools: ['MIT'],
    past_companies: ['Google']
  }
);

// Display high-quality results
results.primary.forEach(connection => {
  displayConnection(connection);
});

// Optionally show uncertain results
if (results.review.length > 0) {
  showReviewSection(results.review);
}
```

### 8. Error Handling

```javascript
// Handle company ambiguity
const handleAmbiguousCompany = async (companyName) => {
  // First try with common domains
  const commonDomains = {
    'Root': 'root.io',
    'Meta': 'meta.com',
    'Stripe': 'stripe.com'
  };
  
  const domain = commonDomains[companyName];
  
  if (!domain) {
    // Show disambiguation UI
    return {
      needsDisambiguation: true,
      suggestions: [
        `${companyName.toLowerCase()}.com`,
        `${companyName.toLowerCase()}.io`,
        `${companyName.toLowerCase()}.co`
      ]
    };
  }
  
  return { company: companyName, domain };
};
```

---

## 🎯 Best Practices

1. **Always include company_domain when available** - This dramatically improves accuracy

2. **Filter client-side by confidence** - Results with confidence >= 0.8 are verified current employees

3. **Prioritize by category** - Recruiters and managers are usually best for referrals

4. **Handle unknowns gracefully** - Don't hide them completely, but de-prioritize

5. **Cache results** - The API returns consistent results, so cache to reduce calls

6. **Show verification status** - Users trust verified results more

7. **Progressive enhancement** - Start with basic search, add context as available

---

## 📊 Metrics to Track

```javascript
// Track search quality metrics
const trackSearchQuality = (results) => {
  analytics.track('search_quality', {
    total_results: results.total,
    verified_count: results.connections.filter(c => c.confidence >= 0.8).length,
    unknown_count: results.connections.filter(c => c.category === 'unknown').length,
    unknown_percentage: (unknownCount / results.total) * 100,
    has_domain: Boolean(searchParams.company_domain),
    categories: {
      recruiters: results.connections.filter(c => c.category === 'recruiter').length,
      managers: results.connections.filter(c => c.category === 'manager').length,
      peers: results.connections.filter(c => c.category === 'peer').length
    }
  });
};
```

This will help you optimize the algorithm further based on real usage!

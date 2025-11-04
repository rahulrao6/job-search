"""
Company name and domain resolution utilities.

Handles:
- Company aliases (Meta = Facebook)
- Domain discovery
- Name normalization
- Ambiguity detection
"""

import re
import os
from typing import Optional, List, Dict, Tuple
from functools import lru_cache


class CompanyResolver:
    """Resolve company names and domains intelligently"""
    
    def __init__(self):
        # Common company aliases
        self.aliases = {
            # Major tech companies
            'meta': ['facebook', 'fb', 'meta platforms'],
            'alphabet': ['google', 'alphabet inc'],
            'amazon': ['aws', 'amazon web services'],
            'microsoft': ['msft', 'microsoft corporation'],
            'apple': ['apple inc', 'aapl'],
            
            # Well-known rebrands
            'x': ['twitter', 'x corp'],
            'block': ['square', 'square inc'],
            'twilio': ['sendgrid'],
            'salesforce': ['slack', 'tableau', 'mulesoft'],
            'adobe': ['figma', 'magento'],
            
            # Company variations
            'jp morgan': ['jpmorgan', 'j.p. morgan', 'jpmorgan chase', 'jpm'],
            'goldman sachs': ['gs', 'goldman'],
            'morgan stanley': ['ms', 'morgan stanley & co'],
            
            # Startups with various names
            'doordash': ['door dash', 'dd'],
            'airbnb': ['air bnb', 'abnb'],
            'databricks': ['data bricks'],
            'snowflake': ['snow'],
            'palantir': ['pltr', 'palantir technologies'],
        }
        
        # Build reverse mapping
        self.name_to_canonical = {}
        for canonical, aliases in self.aliases.items():
            self.name_to_canonical[canonical] = canonical
            for alias in aliases:
                self.name_to_canonical[alias.lower()] = canonical
    
    def normalize_company_name(self, company: str) -> str:
        """
        Normalize company name to canonical form.
        
        Examples:
            "Facebook" -> "Meta"
            "JP Morgan Chase" -> "JP Morgan"
            "Google Inc." -> "Google"
        """
        if not company:
            return company
        
        # Clean and lowercase
        clean = company.lower().strip()
        
        # Remove common suffixes
        suffixes = [
            ' inc', ' corp', ' corporation', ' llc', ' ltd', ' limited',
            ' co', ' company', ' technologies', ' tech', ' systems',
            ' enterprises', ' holdings', ' group', ' international'
        ]
        
        for suffix in suffixes:
            if clean.endswith(suffix):
                clean = clean[:-len(suffix)].strip()
        
        # Check aliases
        if clean in self.name_to_canonical:
            return self.name_to_canonical[clean].title()
        
        # Return cleaned original
        return company.strip()
    
    @lru_cache(maxsize=1000)
    def get_company_domain(self, company: str) -> Optional[str]:
        """
        Get company domain from name.
        
        Uses multiple strategies:
        1. Known mappings
        2. Common patterns
        3. External lookup (future)
        """
        normalized = self.normalize_company_name(company).lower()
        
        # Known domains (expanded from job parser)
        known_domains = {
            # FAANG+
            'google': 'google.com',
            'alphabet': 'abc.xyz',
            'meta': 'meta.com',
            'facebook': 'meta.com',
            'amazon': 'amazon.com',
            'apple': 'apple.com',
            'microsoft': 'microsoft.com',
            'netflix': 'netflix.com',
            
            # Major tech
            'uber': 'uber.com',
            'lyft': 'lyft.com',
            'airbnb': 'airbnb.com',
            'stripe': 'stripe.com',
            'square': 'squareup.com',
            'block': 'block.xyz',
            'twitter': 'twitter.com',
            'x': 'x.com',
            'linkedin': 'linkedin.com',
            'salesforce': 'salesforce.com',
            'oracle': 'oracle.com',
            'ibm': 'ibm.com',
            'intel': 'intel.com',
            'nvidia': 'nvidia.com',
            'amd': 'amd.com',
            
            # Cloud/Enterprise
            'aws': 'aws.amazon.com',
            'google cloud': 'cloud.google.com',
            'azure': 'azure.microsoft.com',
            'databricks': 'databricks.com',
            'snowflake': 'snowflake.com',
            'palantir': 'palantir.com',
            'datadog': 'datadoghq.com',
            'splunk': 'splunk.com',
            'elastic': 'elastic.co',
            'mongodb': 'mongodb.com',
            'confluent': 'confluent.io',
            
            # AI/ML
            'openai': 'openai.com',
            'anthropic': 'anthropic.com',
            'hugging face': 'huggingface.co',
            'weights & biases': 'wandb.ai',
            'cohere': 'cohere.ai',
            'stability ai': 'stability.ai',
            'midjourney': 'midjourney.com',
            
            # Fintech
            'coinbase': 'coinbase.com',
            'robinhood': 'robinhood.com',
            'plaid': 'plaid.com',
            'chime': 'chime.com',
            'affirm': 'affirm.com',
            'klarna': 'klarna.com',
            
            # Other notable
            'spotify': 'spotify.com',
            'pinterest': 'pinterest.com',
            'reddit': 'reddit.com',
            'discord': 'discord.com',
            'slack': 'slack.com',
            'zoom': 'zoom.us',
            'dropbox': 'dropbox.com',
            'box': 'box.com',
            'notion': 'notion.so',
            'figma': 'figma.com',
            'canva': 'canva.com',
            
            # Specific examples
            'root': 'root.io',
            'root insurance': 'joinroot.com',
            'replicant': 'replicant.com',
            'anyscale': 'anyscale.com',
            'voltron data': 'voltrondata.com',
            'moonhub': 'moonhub.ai',
            'lattice': 'lattice.com',
            'vanta': 'vanta.com',
        }
        
        # Check known domains
        if normalized in known_domains:
            return known_domains[normalized]
        
        # Try common patterns
        clean_name = re.sub(r'[^a-z0-9]', '', normalized)
        
        # Try domain discovery methods
        domain = self._discover_domain_from_web(company)
        if domain:
            return domain
            
        # Fallback: common patterns for startups
        # This helps with obscure companies that follow common patterns
        common_tlds = ['.com', '.io', '.ai', '.co', '.dev', '.app']
        
        return None
    
    def _discover_domain_from_web(self, company_name: str) -> Optional[str]:
        """
        Discover company domain using web search.
        Uses DuckDuckGo instant answer API (free, no auth required).
        """
        try:
            import requests
            from urllib.parse import quote
            
            # DuckDuckGo Instant Answer API - free, no auth
            # Good for finding official websites
            query = quote(f"{company_name} official website")
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Check AbstractURL (official website if found)
                if data.get('AbstractURL'):
                    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', data['AbstractURL'])
                    if domain_match:
                        return domain_match.group(1)
                
                # Check Infobox if available
                if data.get('Infobox') and isinstance(data['Infobox'], dict):
                    content = data['Infobox'].get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            label = item.get('label', '').lower()
                            if 'website' in label or 'url' in label:
                                value = item.get('value', '')
                                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', value)
                                if domain_match:
                                    return domain_match.group(1)
        except Exception:
            # Silently fail - domain discovery is optional enhancement
            pass
        
        return None
    
    def is_ambiguous_company(self, company: str) -> bool:
        """
        Check if company name is ambiguous and needs extra verification.
        
        Examples:
            "Root" -> True (could be Root, Root Insurance, etc.)
            "Meta" -> False (well-known unique name)
        """
        normalized = self.normalize_company_name(company).lower()
        
        # Common ambiguous names
        ambiguous = {
            'root', 'branch', 'leaf', 'seed', 'bloom', 'grow',
            'meta', 'data', 'tech', 'labs', 'systems', 'solutions',
            'alpha', 'beta', 'delta', 'gamma', 'sigma',
            'first', 'one', 'next', 'new', 'modern',
            'spark', 'bolt', 'flash', 'swift', 'rapid',
            'blue', 'red', 'green', 'black', 'white',
            'north', 'south', 'east', 'west',
            'peak', 'summit', 'apex', 'zenith',
            'core', 'base', 'prime', 'main',
            'link', 'connect', 'bridge', 'join',
            'wave', 'pulse', 'flow', 'stream',
        }
        
        # Single word companies are often ambiguous
        if ' ' not in normalized and len(normalized) < 8:
            return True
        
        # Check if it's in our ambiguous set
        if normalized in ambiguous:
            return True
        
        # Check if it's a common word
        words = normalized.split()
        if len(words) == 1 and words[0] in ambiguous:
            return True
        
        return False
    
    def get_company_patterns(self, company: str, domain: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get search patterns for a company.
        
        Returns patterns optimized for different contexts:
        - linkedin: LinkedIn-specific patterns
        - general: General web search patterns
        - strict: High-precision patterns
        """
        normalized = self.normalize_company_name(company)
        patterns = {
            'linkedin': [],
            'general': [],
            'strict': [],
        }
        
        # LinkedIn patterns
        company_slug = normalized.lower().replace(' ', '-')
        patterns['linkedin'].append(f'/company/{company_slug}')
        patterns['linkedin'].append(f'at {normalized}')
        patterns['linkedin'].append(f'@ {normalized}')
        
        # With domain
        if domain:
            patterns['linkedin'].append(f'{normalized} ({domain})')
            patterns['linkedin'].append(f'at {normalized} ({domain})')
            domain_slug = domain.replace('.', '-')
            patterns['linkedin'].append(f'/company/{domain_slug}')
        
        # General patterns
        patterns['general'].append(f'"{normalized}"')
        patterns['general'].append(f'{normalized} employee')
        patterns['general'].append(f'working at {normalized}')
        
        # Strict patterns (require more context)
        patterns['strict'].append(f'currently at {normalized}')
        patterns['strict'].append(f'{normalized} - Present')
        if domain:
            patterns['strict'].append(f'{normalized} {domain}')
            patterns['strict'].append(f'@{domain}')
        
        return patterns
    
    def calculate_company_match_score(self, text: str, company: str, 
                                    domain: Optional[str] = None) -> float:
        """
        Calculate how likely this text is about someone at the company.
        
        Enhanced with:
        - Date pattern parsing for "Present/Current" indicators
        - Enhanced negative signal detection with proximity
        - Recency signal boosting
        
        Returns score 0.0 to 1.0 based on multiple signals.
        """
        text_lower = text.lower()
        company_lower = company.lower()
        score = 0.0
        
        # Check for negative signals first with enhanced proximity checking
        negative_signals = {
            'former': 2.0,
            'ex-': 2.0,
            'previously': 1.5,
            'formerly': 2.0,
            'alumni': 1.0,
            'was at': 1.0,
            'worked at': 1.0,
            'used to': 1.0,
            'past': 1.0
        }
        
        negative_score = 0.0
        for signal, weight in negative_signals.items():
            if signal in text_lower and company_lower in text_lower:
                # Check proximity
                signal_pos = text_lower.find(signal)
                company_pos = text_lower.find(company_lower)
                if company_pos != -1 and abs(signal_pos - company_pos) < 50:
                    negative_score += weight
                    if negative_score > 2.0:
                        return 0.0  # Definitely not current
        
        # Date pattern parsing for LinkedIn date formats
        date_patterns = [
            r'(\w+\s+\d{4})\s*[-–]\s*(Present|Current)',  # "Jan 2023 - Present"
            r'(\d{4})\s*[-–]\s*(Present|Current)',        # "2023 - Present"
        ]
        
        has_present_date = False
        for pattern in date_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                end_date = match.group(2) if len(match.groups()) >= 2 else None
                if end_date and end_date.lower() in ['present', 'current']:
                    has_present_date = True
                    score += 0.2  # Boost for "Present" indicator
                    break
        
        # Positive signals with weights
        if domain and domain.lower() in text_lower:
            score += 0.4  # Strong signal
        
        # Current employment patterns
        current_patterns = [
            (f' at {company_lower}', 0.3),
            (f' @ {company_lower}', 0.3),
            (f'{company_lower} |', 0.25),
            (f'| {company_lower}', 0.25),
            (f', {company_lower}', 0.2),
            (f'currently at {company_lower}', 0.4),
            (f'{company_lower} - present', 0.4),
        ]
        
        for pattern, weight in current_patterns:
            if pattern in text_lower:
                score += weight
                break  # Only count one pattern
        
        # LinkedIn URL patterns
        company_slug = company_lower.replace(' ', '-')
        if f'/company/{company_slug}' in text_lower:
            score += 0.3
        
        # Professional context
        if company_lower in text_lower:
            # Check for professional keywords nearby
            prof_keywords = [
                'engineer', 'developer', 'manager', 'designer',
                'scientist', 'analyst', 'director', 'lead'
            ]
            
            for keyword in prof_keywords:
                if keyword in text_lower:
                    score += 0.1
                    break
        
        # Recency signal boost (if has present date, boost more)
        if has_present_date:
            score += 0.1  # Additional boost for explicit "Present" date
        
        # Apply negative score penalty
        if negative_score > 0:
            score = max(0.0, score - (negative_score * 0.2))
        
        # Basic company mention (fallback)
        if score == 0.0 and company_lower in text_lower:
            # Company is mentioned but no strong signals
            # Give minimal score to allow through
            score = 0.2
        
        # Cap at 1.0
        return min(1.0, score)

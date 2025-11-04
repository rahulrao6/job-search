"""Web scraping source implementations"""

from .github_profiles import GitHubScraper
from .google_search import GoogleSearchScraper

__all__ = [
    "GitHubScraper", 
    "GoogleSearchScraper",
]

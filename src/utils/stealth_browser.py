"""Stealth browser using Playwright"""

import asyncio
import random
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.utils.rate_limiter import get_rate_limiter


class StealthBrowser:
    """
    Playwright-based browser with anti-detection measures.
    
    Features:
    - Stealth mode to avoid detection
    - Random delays
    - Fingerprint rotation
    - Cookie management
    """
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.rate_limiter = get_rate_limiter()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def start(self):
        """Start the browser"""
        self.playwright = await async_playwright().start()
        
        # Launch options
        launch_options = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        }
        
        if self.proxy:
            # Parse proxy
            # Format: http://user:pass@host:port or http://host:port
            launch_options["proxy"] = {"server": self.proxy}
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Create context with random user agent and viewport
        context_options = self._get_random_context_options()
        self.context = await self.browser.new_context(**context_options)
        
        # Add stealth scripts
        await self._add_stealth_scripts(self.context)
    
    async def close(self):
        """Close the browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def new_page(self) -> Page:
        """Create a new page"""
        if not self.context:
            await self.start()
        
        page = await self.context.new_page()
        
        # Add random delays to navigation
        await page.set_default_navigation_timeout(30000)
        await page.set_default_timeout(30000)
        
        return page
    
    async def goto(self, page: Page, url: str, wait_after: bool = True) -> None:
        """Navigate to URL with rate limiting and delays"""
        # Rate limit
        self.rate_limiter.wait_if_needed("browser")
        
        # Navigate
        await page.goto(url, wait_until="domcontentloaded")
        
        # Random delay to appear human
        if wait_after:
            delay = random.uniform(2.0, 5.0)
            await asyncio.sleep(delay)
    
    async def set_cookies(self, cookies: list):
        """Set cookies for the browser context"""
        if self.context:
            await self.context.add_cookies(cookies)
    
    def _get_random_context_options(self) -> Dict[str, Any]:
        """Generate random browser context options"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]
        
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1536, "height": 864},
        ]
        
        return {
            "user_agent": random.choice(user_agents),
            "viewport": random.choice(viewports),
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }
    
    async def _add_stealth_scripts(self, context: BrowserContext):
        """Add scripts to make browser appear more human"""
        # Override navigator.webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Add plugins
        await context.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        # Add languages
        await context.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)


# Helper function for synchronous usage
def create_stealth_browser(headless: bool = True, proxy: Optional[str] = None) -> StealthBrowser:
    """Factory function to create stealth browser"""
    return StealthBrowser(headless=headless, proxy=proxy)


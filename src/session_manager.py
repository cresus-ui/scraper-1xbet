"""Session manager for 1xbet scraper using Playwright.

This module handles browser sessions, page navigation, and dynamic content loading
for scraping 1xbet.com with proper error handling and retry mechanisms.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from apify import Actor
import random
import time

from config import ConfigManager, ScrapingConfig


class SessionManager:
    """Manages browser sessions and page interactions for scraping."""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.request_count = 0
        self.last_request_time = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()
    
    async def start_session(self) -> None:
        """Initialize browser session with proper configuration."""
        try:
            self.logger.info("Starting browser session...")
            
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Browser launch options
            launch_options = {
                'headless': not self.config.debug_mode,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            }
            
            # Launch browser
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # Create context with proper settings
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': self._get_random_user_agent(),
                'locale': 'en-US',
                'timezone_id': 'UTC'
            }
            
            # Add proxy configuration if available
            proxy_config = self.config.get_proxy_config()
            if proxy_config:
                context_options['proxy'] = proxy_config
            
            self.context = await self.browser.new_context(**context_options)
            
            # Set extra headers
            await self.context.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Create page
            self.page = await self.context.new_page()
            
            # Set page timeouts
            self.page.set_default_timeout(30000)  # 30 seconds
            self.page.set_default_navigation_timeout(60000)  # 60 seconds
            
            # Block unnecessary resources to speed up loading
            await self.page.route('**/*', self._handle_route)
            
            self.logger.info("Browser session started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start browser session: {str(e)}")
            await self.close_session()
            raise
    
    async def close_session(self) -> None:
        """Close browser session and cleanup resources."""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            self.logger.info("Browser session closed")
            
        except Exception as e:
            self.logger.error(f"Error closing browser session: {str(e)}")
    
    async def navigate_to_url(self, url: str, wait_for_selector: Optional[str] = None) -> bool:
        """Navigate to URL with retry mechanism and optional element wait."""
        if not self.page:
            raise RuntimeError("Browser session not started")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                await self._apply_rate_limit()
                
                self.logger.info(f"Navigating to: {url} (attempt {attempt + 1})")
                
                # Navigate to URL
                response = await self.page.goto(url, wait_until='domcontentloaded')
                
                if response and response.status >= 400:
                    raise Exception(f"HTTP {response.status}: {response.status_text}")
                
                # Wait for specific selector if provided
                if wait_for_selector:
                    await self.page.wait_for_selector(wait_for_selector, timeout=10000)
                
                # Wait for page to be fully loaded
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                
                self.logger.info(f"Successfully navigated to: {url}")
                return True
                
            except Exception as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to navigate to {url} after {max_retries} attempts")
                    return False
        
        return False
    
    async def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for element to appear on page."""
        if not self.page:
            raise RuntimeError("Browser session not started")
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.warning(f"Element not found: {selector} - {str(e)}")
            return False
    
    async def click_element(self, selector: str, timeout: int = 10000) -> bool:
        """Click element with error handling."""
        if not self.page:
            raise RuntimeError("Browser session not started")
        
        try:
            await self.page.click(selector, timeout=timeout)
            await asyncio.sleep(1)  # Wait for potential page changes
            return True
        except Exception as e:
            self.logger.warning(f"Failed to click element: {selector} - {str(e)}")
            return False
    
    async def scroll_to_load_content(self, max_scrolls: int = 5) -> None:
        """Scroll page to load dynamic content."""
        if not self.page:
            raise RuntimeError("Browser session not started")
        
        try:
            for i in range(max_scrolls):
                # Scroll down
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
                
                # Check if new content loaded
                current_height = await self.page.evaluate('document.body.scrollHeight')
                await asyncio.sleep(1)
                new_height = await self.page.evaluate('document.body.scrollHeight')
                
                if current_height == new_height:
                    break
                    
                self.logger.debug(f"Scroll {i + 1}: Page height changed from {current_height} to {new_height}")
            
        except Exception as e:
            self.logger.warning(f"Error during scrolling: {str(e)}")
    
    async def get_page_content(self) -> str:
        """Get current page HTML content."""
        if not self.page:
            raise RuntimeError("Browser session not started")
        
        return await self.page.content()
    
    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript on the page."""
        if not self.page:
            raise RuntimeError("Browser session not started")
        
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            self.logger.warning(f"Script execution failed: {str(e)}")
            return None
    
    async def take_screenshot(self, path: str) -> bool:
        """Take screenshot for debugging."""
        if not self.page:
            return False
        
        try:
            await self.page.screenshot(path=path, full_page=True)
            return True
        except Exception as e:
            self.logger.warning(f"Screenshot failed: {str(e)}")
            return False
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent string."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        return random.choice(user_agents)
    
    async def _handle_route(self, route) -> None:
        """Handle page routes to block unnecessary resources."""
        # Block images, fonts, and other non-essential resources to speed up loading
        if route.request.resource_type in ['image', 'font', 'media']:
            await route.abort()
        else:
            await route.continue_()
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.config.delay_between_requests:
            sleep_time = self.config.delay_between_requests - time_since_last_request
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        if self.config.debug_mode:
            self.logger.debug(f"Request #{self.request_count} - Rate limit applied")
"""Configuration module for 1xbet scraper.

This module handles input validation and configuration management
using Pydantic models for type safety and validation.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, model_validator
from apify import Actor
import logging


class ProxyConfig(BaseModel):
    """Proxy configuration model."""
    use_apify_proxy: bool = Field(default=True, alias="useApifyProxy")
    proxy_groups: Optional[List[str]] = Field(default=None, alias="proxyGroups")
    country_code: Optional[str] = Field(default=None, alias="countryCode")


class ScrapingConfig(BaseModel):
    """Main configuration model for the 1xbet scraper."""
    
    # Sports and filtering
    sports: List[str] = Field(
        default=["football"],
        description="List of sports to extract data from"
    )
    start_date: Optional[date] = Field(
        default=None,
        alias="startDate",
        description="Start date for data extraction"
    )
    end_date: Optional[date] = Field(
        default=None,
        alias="endDate",
        description="End date for data extraction"
    )
    competitions: Optional[List[str]] = Field(
        default=None,
        description="Filter by specific competitions/leagues"
    )
    countries: Optional[List[str]] = Field(
        default=None,
        description="Filter matches by countries"
    )
    
    # Data extraction options
    include_pre_match: bool = Field(
        default=True,
        alias="includePreMatch",
        description="Extract pre-match data"
    )
    include_post_match: bool = Field(
        default=True,
        alias="includePostMatch",
        description="Extract post-match data"
    )
    include_weather: bool = Field(
        default=False,
        alias="includeWeather",
        description="Extract weather conditions"
    )
    include_lineups: bool = Field(
        default=False,
        alias="includeLineups",
        description="Extract team lineups"
    )
    include_statistics: bool = Field(
        default=True,
        alias="includeStatistics",
        description="Extract detailed statistics"
    )
    
    # Limits and performance
    max_matches_per_sport: int = Field(
        default=100,
        ge=1,
        le=1000,
        alias="maxMatchesPerSport",
        description="Maximum matches per sport"
    )
    delay_between_requests: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        alias="delayBetweenRequests",
        description="Delay between requests in seconds"
    )
    
    # Technical settings
    proxy_configuration: Optional[ProxyConfig] = Field(
        default=None,
        alias="proxyConfiguration"
    )
    respect_robots_txt: bool = Field(
        default=True,
        alias="respectRobotsText"
    )
    debug_mode: bool = Field(
        default=False,
        alias="debugMode"
    )
    
    @validator('sports')
    def validate_sports(cls, v):
        """Validate sports list."""
        valid_sports = {
            'football', 'tennis', 'basketball', 'hockey', 
            'volleyball', 'baseball', 'handball'
        }
        for sport in v:
            if sport not in valid_sports:
                raise ValueError(f"Invalid sport: {sport}. Valid sports: {valid_sports}")
        return v
    
    @model_validator(mode='after')
    def validate_dates(self):
        """Validate date range."""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("Start date must be before end date")
            
            # Check if date range is reasonable (not more than 1 year)
            if (self.end_date - self.start_date).days > 365:
                raise ValueError("Date range cannot exceed 365 days")
        
        return self
    
    @model_validator(mode='after')
    def validate_extraction_options(self):
        """Ensure at least one extraction option is enabled."""
        if not self.include_pre_match and not self.include_post_match:
            raise ValueError("At least one of includePreMatch or includePostMatch must be true")
        
        return self


class ConfigManager:
    """Configuration manager for the scraper."""
    
    def __init__(self):
        self.config: Optional[ScrapingConfig] = None
        self.logger = logging.getLogger(__name__)
    
    async def load_config(self) -> ScrapingConfig:
        """Load and validate configuration from Apify input."""
        try:
            # Get input from Apify
            actor_input = await Actor.get_input() or {}
            
            # Validate and create config
            self.config = ScrapingConfig(**actor_input)
            
            # Log configuration
            if self.config.debug_mode:
                self.logger.info(f"Loaded configuration: {self.config.dict()}")
            else:
                self.logger.info(f"Loaded configuration for sports: {self.config.sports}")
            
            return self.config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise ValueError(f"Invalid configuration: {str(e)}")
    
    def get_config(self) -> ScrapingConfig:
        """Get current configuration."""
        if self.config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self.config
    
    def get_base_urls(self) -> Dict[str, str]:
        """Get base URLs for different sports."""
        base_urls = {
            'football': 'https://1xbet.com/en/live/football',
            'tennis': 'https://1xbet.com/en/live/tennis',
            'basketball': 'https://1xbet.com/en/live/basketball',
            'hockey': 'https://1xbet.com/en/live/hockey',
            'volleyball': 'https://1xbet.com/en/live/volleyball',
            'baseball': 'https://1xbet.com/en/live/baseball',
            'handball': 'https://1xbet.com/en/live/handball'
        }
        
        return {sport: base_urls[sport] for sport in self.config.sports if sport in base_urls}
    
    def should_extract_weather(self) -> bool:
        """Check if weather extraction is enabled for outdoor sports."""
        if not self.config.include_weather:
            return False
        
        outdoor_sports = {'football', 'baseball', 'tennis'}
        return any(sport in outdoor_sports for sport in self.config.sports)
    
    def get_request_delay(self) -> float:
        """Get delay between requests."""
        return self.config.delay_between_requests
    
    def get_proxy_config(self) -> Optional[Dict[str, Any]]:
        """Get proxy configuration for requests."""
        if not self.config.proxy_configuration:
            return None
        
        proxy_config = self.config.proxy_configuration.dict(by_alias=True)
        return proxy_config if proxy_config.get('useApifyProxy') else None
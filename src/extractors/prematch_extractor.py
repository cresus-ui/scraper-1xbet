"""Pre-match data extractor for 1xbet scraper.

This module handles extraction of pre-match data including team information,
odds, weather conditions, and team lineups from 1xbet.com.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session_manager import SessionManager
from config import ScrapingConfig


class PreMatchExtractor:
    """Extracts pre-match data from 1xbet pages."""
    
    def __init__(self, session_manager: SessionManager, config: ScrapingConfig):
        self.session = session_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def extract_matches_list(self, sport: str, page_url: str) -> List[Dict[str, Any]]:
        """Extract list of matches for a specific sport."""
        try:
            self.logger.info(f"Extracting matches list for {sport} from {page_url}")
            
            # Navigate to the sport page
            success = await self.session.navigate_to_url(
                page_url, 
                wait_for_selector='.c-events'
            )
            
            if not success:
                self.logger.error(f"Failed to load {sport} page")
                return []
            
            # Wait for matches to load
            await self.session.wait_for_element('.c-events__item', timeout=15000)
            
            # Scroll to load more matches
            await self.session.scroll_to_load_content(max_scrolls=3)
            
            # Get page content
            content = await self.session.get_page_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract match elements
            match_elements = soup.find_all('div', class_='c-events__item')
            
            matches = []
            for element in match_elements[:self.config.max_matches_per_sport]:
                match_data = await self._extract_match_basic_info(element, sport)
                if match_data:
                    matches.append(match_data)
            
            self.logger.info(f"Extracted {len(matches)} matches for {sport}")
            return matches
            
        except Exception as e:
            self.logger.error(f"Error extracting matches list for {sport}: {str(e)}")
            return []
    
    async def extract_detailed_match_data(self, match_basic: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed data for a specific match."""
        try:
            match_url = match_basic.get('match_url')
            if not match_url:
                self.logger.warning("No match URL provided")
                return match_basic
            
            self.logger.info(f"Extracting detailed data for match: {match_basic.get('match_id')}")
            
            # Navigate to match page
            success = await self.session.navigate_to_url(
                match_url,
                wait_for_selector='.c-bet-group'
            )
            
            if not success:
                self.logger.warning(f"Failed to load match page: {match_url}")
                return match_basic
            
            # Get page content
            content = await self.session.get_page_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract detailed information
            detailed_data = match_basic.copy()
            
            # Extract odds
            if self.config.include_pre_match:
                odds_data = await self._extract_odds_data(soup)
                detailed_data['odds'] = odds_data
            
            # Extract team lineups
            if self.config.include_lineups:
                lineups = await self._extract_lineups(soup)
                detailed_data['lineups'] = lineups
            
            # Extract weather (for outdoor sports)
            if self.config.include_weather and self._is_outdoor_sport(match_basic.get('sport')):
                weather = await self._extract_weather_data(soup)
                detailed_data['weather'] = weather
            
            # Extract additional match statistics
            stats = await self._extract_match_statistics(soup)
            detailed_data['statistics'] = stats
            
            return detailed_data
            
        except Exception as e:
            self.logger.error(f"Error extracting detailed match data: {str(e)}")
            return match_basic
    
    async def _extract_match_basic_info(self, element, sport: str) -> Optional[Dict[str, Any]]:
        """Extract basic match information from match element."""
        try:
            # Extract match ID
            match_id = self._extract_match_id(element)
            if not match_id:
                return None
            
            # Extract teams
            teams = self._extract_teams_info(element)
            if not teams:
                return None
            
            # Extract match time
            match_time = self._extract_match_time(element)
            
            # Extract match URL
            match_url = self._extract_match_url(element)
            
            # Extract competition
            competition = self._extract_competition(element)
            
            return {
                'match_id': match_id,
                'sport': sport,
                'teams': teams,
                'match_time': match_time,
                'match_url': match_url,
                'competition': competition,
                'extracted_at': datetime.now(timezone.utc).isoformat(),
                'status': 'pre_match'
            }
            
        except Exception as e:
            self.logger.warning(f"Error extracting basic match info: {str(e)}")
            return None
    
    def _extract_match_id(self, element) -> Optional[str]:
        """Extract match ID from element."""
        try:
            # Look for data attributes that might contain match ID
            for attr in ['data-id', 'data-match-id', 'data-event-id']:
                if element.has_attr(attr):
                    return element[attr]
            
            # Try to extract from class names
            classes = element.get('class', [])
            for cls in classes:
                if 'id-' in cls:
                    return cls.split('id-')[-1]
            
            # Generate ID from team names and time if no explicit ID found
            teams_elem = element.find('div', class_='c-events__teams')
            if teams_elem:
                teams_text = teams_elem.get_text(strip=True)
                return f"match_{hash(teams_text) % 1000000}"
            
            return None
            
        except Exception:
            return None
    
    def _extract_teams_info(self, element) -> Optional[Dict[str, Any]]:
        """Extract teams information."""
        try:
            teams_container = element.find('div', class_='c-events__teams')
            if not teams_container:
                return None
            
            # Try different selectors for team names
            team_elements = teams_container.find_all('span', class_='c-events__team')
            if not team_elements and len(team_elements) < 2:
                # Alternative selector
                team_elements = teams_container.find_all('div', class_='team-name')
            
            if len(team_elements) >= 2:
                return {
                    'home_team': {
                        'name': team_elements[0].get_text(strip=True),
                        'logo_url': self._extract_team_logo(team_elements[0])
                    },
                    'away_team': {
                        'name': team_elements[1].get_text(strip=True),
                        'logo_url': self._extract_team_logo(team_elements[1])
                    }
                }
            
            # Fallback: try to parse from text
            teams_text = teams_container.get_text(strip=True)
            if ' - ' in teams_text:
                team_names = teams_text.split(' - ')
                if len(team_names) == 2:
                    return {
                        'home_team': {'name': team_names[0].strip(), 'logo_url': None},
                        'away_team': {'name': team_names[1].strip(), 'logo_url': None}
                    }
            
            return None
            
        except Exception:
            return None
    
    def _extract_team_logo(self, team_element) -> Optional[str]:
        """Extract team logo URL."""
        try:
            img = team_element.find('img')
            if img and img.has_attr('src'):
                return img['src']
            return None
        except Exception:
            return None
    
    def _extract_match_time(self, element) -> Optional[str]:
        """Extract match time."""
        try:
            # Look for time elements
            time_selectors = [
                '.c-events__time',
                '.match-time',
                '.event-time',
                '[data-time]'
            ]
            
            for selector in time_selectors:
                time_elem = element.select_one(selector)
                if time_elem:
                    time_text = time_elem.get_text(strip=True)
                    if time_text:
                        return self._parse_match_time(time_text)
            
            return None
            
        except Exception:
            return None
    
    def _parse_match_time(self, time_text: str) -> Optional[str]:
        """Parse match time string to ISO format."""
        try:
            # Handle different time formats
            time_patterns = [
                r'(\d{1,2}):(\d{2})',  # HH:MM
                r'(\d{1,2})\.(\d{2})',  # HH.MM
                r'(\d{1,2})h(\d{2})'   # HHhMM
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, time_text)
                if match:
                    hours, minutes = match.groups()
                    # Assume today's date for now
                    today = datetime.now(timezone.utc).date()
                    match_datetime = datetime.combine(
                        today, 
                        datetime.strptime(f"{hours}:{minutes}", "%H:%M").time()
                    ).replace(tzinfo=timezone.utc)
                    return match_datetime.isoformat()
            
            return time_text  # Return original if parsing fails
            
        except Exception:
            return time_text
    
    def _extract_match_url(self, element) -> Optional[str]:
        """Extract match detail URL."""
        try:
            # Look for links
            link = element.find('a', href=True)
            if link:
                href = link['href']
                if href.startswith('/'):
                    return f"https://1xbet.com{href}"
                return href
            
            return None
            
        except Exception:
            return None
    
    def _extract_competition(self, element) -> Optional[str]:
        """Extract competition/league name."""
        try:
            # Look for competition elements
            comp_selectors = [
                '.c-events__league',
                '.competition',
                '.league-name',
                '.tournament'
            ]
            
            for selector in comp_selectors:
                comp_elem = element.select_one(selector)
                if comp_elem:
                    return comp_elem.get_text(strip=True)
            
            return None
            
        except Exception:
            return None
    
    async def _extract_odds_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract betting odds data."""
        try:
            odds_data = {
                'main_odds': {},
                'additional_odds': {},
                'total_markets': 0
            }
            
            # Extract main odds (1X2, Over/Under, etc.)
            main_odds_container = soup.find('div', class_='c-bet-group')
            if main_odds_container:
                odds_data['main_odds'] = self._parse_main_odds(main_odds_container)
            
            # Count total markets
            all_odds = soup.find_all('div', class_='c-bet')
            odds_data['total_markets'] = len(all_odds)
            
            return odds_data
            
        except Exception as e:
            self.logger.warning(f"Error extracting odds data: {str(e)}")
            return {}
    
    def _parse_main_odds(self, container) -> Dict[str, Any]:
        """Parse main betting odds."""
        try:
            odds = {}
            
            # Look for 1X2 odds
            bet_buttons = container.find_all('button', class_='c-bet__pick')
            if len(bet_buttons) >= 3:
                odds['1x2'] = {
                    'home_win': self._extract_odd_value(bet_buttons[0]),
                    'draw': self._extract_odd_value(bet_buttons[1]),
                    'away_win': self._extract_odd_value(bet_buttons[2])
                }
            
            return odds
            
        except Exception:
            return {}
    
    def _extract_odd_value(self, button) -> Optional[float]:
        """Extract odd value from button element."""
        try:
            odd_text = button.get_text(strip=True)
            # Remove any non-numeric characters except decimal point
            odd_clean = re.sub(r'[^\d.]', '', odd_text)
            return float(odd_clean) if odd_clean else None
        except Exception:
            return None
    
    async def _extract_lineups(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract team lineups if available."""
        try:
            lineups = {
                'home_team': {'players': []},
                'away_team': {'players': []},
                'available': False
            }
            
            # Look for lineup sections
            lineup_container = soup.find('div', class_='lineups')
            if lineup_container:
                lineups['available'] = True
                # Extract player information
                # This would need to be customized based on actual page structure
            
            return lineups
            
        except Exception as e:
            self.logger.warning(f"Error extracting lineups: {str(e)}")
            return {'available': False}
    
    async def _extract_weather_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract weather data for outdoor sports."""
        try:
            weather = {
                'available': False,
                'temperature': None,
                'conditions': None,
                'humidity': None,
                'wind_speed': None
            }
            
            # Look for weather information
            weather_container = soup.find('div', class_='weather')
            if weather_container:
                weather['available'] = True
                # Extract weather details based on actual page structure
            
            return weather
            
        except Exception as e:
            self.logger.warning(f"Error extracting weather data: {str(e)}")
            return {'available': False}
    
    async def _extract_match_statistics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract additional match statistics."""
        try:
            stats = {
                'head_to_head': [],
                'recent_form': {
                    'home_team': [],
                    'away_team': []
                },
                'available': False
            }
            
            # Look for statistics sections
            stats_container = soup.find('div', class_='statistics')
            if stats_container:
                stats['available'] = True
                # Extract statistical data
            
            return stats
            
        except Exception as e:
            self.logger.warning(f"Error extracting match statistics: {str(e)}")
            return {'available': False}
    
    def _is_outdoor_sport(self, sport: str) -> bool:
        """Check if sport is typically played outdoors."""
        outdoor_sports = {'football', 'baseball', 'tennis'}
        return sport.lower() in outdoor_sports
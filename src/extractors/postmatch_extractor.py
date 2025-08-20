"""Post-match data extractor for 1xbet scraper.

This module handles extraction of post-match data including match results,
detailed statistics, match events, and player performances from 1xbet.com.
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
from .prematch_extractor import PreMatchExtractor


class PostMatchExtractor(PreMatchExtractor):
    """Extracts post-match data from 1xbet pages."""
    
    def __init__(self, session_manager: SessionManager, config: ScrapingConfig):
        super().__init__(session_manager, config)
        self.logger = logging.getLogger(__name__)
    
    async def extract_finished_matches(self, sport: str, page_url: str) -> List[Dict[str, Any]]:
        """Extract list of finished matches for a specific sport."""
        try:
            self.logger.info(f"Extracting finished matches for {sport} from {page_url}")
            
            # Modify URL to show finished matches
            finished_url = self._get_finished_matches_url(page_url)
            
            # Navigate to the finished matches page
            success = await self.session.navigate_to_url(
                finished_url, 
                wait_for_selector='.c-events'
            )
            
            if not success:
                self.logger.error(f"Failed to load finished {sport} matches page")
                return []
            
            # Wait for matches to load
            await self.session.wait_for_element('.c-events__item', timeout=15000)
            
            # Scroll to load more matches
            await self.session.scroll_to_load_content(max_scrolls=3)
            
            # Get page content
            content = await self.session.get_page_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract finished match elements
            match_elements = soup.find_all('div', class_='c-events__item')
            
            matches = []
            for element in match_elements[:self.config.max_matches_per_sport]:
                match_data = await self._extract_finished_match_basic_info(element, sport)
                if match_data:
                    matches.append(match_data)
            
            self.logger.info(f"Extracted {len(matches)} finished matches for {sport}")
            return matches
            
        except Exception as e:
            self.logger.error(f"Error extracting finished matches for {sport}: {str(e)}")
            return []
    
    async def extract_detailed_match_results(self, match_basic: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed results and statistics for a finished match."""
        try:
            match_url = match_basic.get('match_url')
            if not match_url:
                self.logger.warning("No match URL provided")
                return match_basic
            
            self.logger.info(f"Extracting detailed results for match: {match_basic.get('match_id')}")
            
            # Navigate to match results page
            success = await self.session.navigate_to_url(
                match_url,
                wait_for_selector='.match-result'
            )
            
            if not success:
                self.logger.warning(f"Failed to load match results page: {match_url}")
                return match_basic
            
            # Get page content
            content = await self.session.get_page_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract detailed information
            detailed_data = match_basic.copy()
            
            # Extract final score
            score_data = await self._extract_final_score(soup)
            detailed_data['final_score'] = score_data
            
            # Extract match events (goals, cards, substitutions)
            events = await self._extract_match_events(soup)
            detailed_data['events'] = events
            
            # Extract detailed statistics
            if self.config.include_statistics:
                statistics = await self._extract_detailed_statistics(soup)
                detailed_data['statistics'] = statistics
            
            # Extract player performances
            player_stats = await self._extract_player_statistics(soup)
            detailed_data['player_statistics'] = player_stats
            
            # Extract match summary
            summary = await self._extract_match_summary(soup)
            detailed_data['summary'] = summary
            
            return detailed_data
            
        except Exception as e:
            self.logger.error(f"Error extracting detailed match results: {str(e)}")
            return match_basic
    
    def _get_finished_matches_url(self, live_url: str) -> str:
        """Convert live matches URL to finished matches URL."""
        # Replace 'live' with 'results' or add results parameter
        if '/live/' in live_url:
            return live_url.replace('/live/', '/results/')
        elif '?' in live_url:
            return f"{live_url}&period=finished"
        else:
            return f"{live_url}?period=finished"
    
    async def _extract_finished_match_basic_info(self, element, sport: str) -> Optional[Dict[str, Any]]:
        """Extract basic information from finished match element."""
        try:
            # Extract match ID
            match_id = self._extract_match_id(element)
            if not match_id:
                return None
            
            # Extract teams
            teams = self._extract_teams_info(element)
            if not teams:
                return None
            
            # Extract final score
            score = self._extract_score_from_element(element)
            
            # Extract match date/time
            match_time = self._extract_finished_match_time(element)
            
            # Extract match URL
            match_url = self._extract_match_url(element)
            
            # Extract competition
            competition = self._extract_competition(element)
            
            return {
                'match_id': match_id,
                'sport': sport,
                'teams': teams,
                'final_score': score,
                'match_time': match_time,
                'match_url': match_url,
                'competition': competition,
                'extracted_at': datetime.now(timezone.utc).isoformat(),
                'status': 'finished'
            }
            
        except Exception as e:
            self.logger.warning(f"Error extracting finished match basic info: {str(e)}")
            return None
    
    def _extract_score_from_element(self, element) -> Optional[Dict[str, Any]]:
        """Extract score from match element."""
        try:
            # Look for score elements
            score_selectors = [
                '.c-events__score',
                '.match-score',
                '.score',
                '.result'
            ]
            
            for selector in score_selectors:
                score_elem = element.select_one(selector)
                if score_elem:
                    score_text = score_elem.get_text(strip=True)
                    return self._parse_score(score_text)
            
            return None
            
        except Exception:
            return None
    
    def _parse_score(self, score_text: str) -> Optional[Dict[str, Any]]:
        """Parse score string into structured data."""
        try:
            # Handle different score formats: "2:1", "2-1", "2 1"
            score_patterns = [
                r'(\d+):(\d+)',  # 2:1
                r'(\d+)-(\d+)',  # 2-1
                r'(\d+)\s+(\d+)'  # 2 1
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, score_text)
                if match:
                    home_score, away_score = match.groups()
                    return {
                        'home_score': int(home_score),
                        'away_score': int(away_score),
                        'raw_score': score_text
                    }
            
            return {'raw_score': score_text}
            
        except Exception:
            return None
    
    async def _extract_final_score(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract detailed final score information."""
        try:
            score_data = {
                'final_score': None,
                'half_time_score': None,
                'extra_time_score': None,
                'penalty_score': None
            }
            
            # Extract main score
            main_score = soup.find('div', class_='match-score')
            if main_score:
                score_data['final_score'] = self._parse_score(main_score.get_text(strip=True))
            
            # Extract half-time score
            ht_score = soup.find('span', class_='half-time-score')
            if ht_score:
                score_data['half_time_score'] = self._parse_score(ht_score.get_text(strip=True))
            
            return score_data
            
        except Exception as e:
            self.logger.warning(f"Error extracting final score: {str(e)}")
            return {}
    
    async def _extract_match_events(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract match events (goals, cards, substitutions)."""
        try:
            events = []
            
            # Look for events container
            events_container = soup.find('div', class_='match-events')
            if not events_container:
                events_container = soup.find('div', class_='timeline')
            
            if events_container:
                event_elements = events_container.find_all('div', class_='event')
                
                for event_elem in event_elements:
                    event_data = self._parse_match_event(event_elem)
                    if event_data:
                        events.append(event_data)
            
            return events
            
        except Exception as e:
            self.logger.warning(f"Error extracting match events: {str(e)}")
            return []
    
    def _parse_match_event(self, event_elem) -> Optional[Dict[str, Any]]:
        """Parse individual match event."""
        try:
            event_data = {
                'minute': None,
                'type': None,
                'player': None,
                'team': None,
                'description': None
            }
            
            # Extract minute
            minute_elem = event_elem.find('span', class_='minute')
            if minute_elem:
                minute_text = minute_elem.get_text(strip=True)
                event_data['minute'] = re.sub(r'[^\d]', '', minute_text)
            
            # Extract event type
            type_elem = event_elem.find('span', class_='event-type')
            if type_elem:
                event_data['type'] = type_elem.get_text(strip=True)
            
            # Extract player name
            player_elem = event_elem.find('span', class_='player')
            if player_elem:
                event_data['player'] = player_elem.get_text(strip=True)
            
            # Extract description
            event_data['description'] = event_elem.get_text(strip=True)
            
            return event_data if event_data['minute'] else None
            
        except Exception:
            return None
    
    async def _extract_detailed_statistics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract detailed match statistics."""
        try:
            stats = {
                'possession': {'home': None, 'away': None},
                'shots': {'home': None, 'away': None},
                'shots_on_target': {'home': None, 'away': None},
                'corners': {'home': None, 'away': None},
                'fouls': {'home': None, 'away': None},
                'yellow_cards': {'home': None, 'away': None},
                'red_cards': {'home': None, 'away': None},
                'offsides': {'home': None, 'away': None},
                'available': False
            }
            
            # Look for statistics container
            stats_container = soup.find('div', class_='match-statistics')
            if not stats_container:
                stats_container = soup.find('div', class_='statistics')
            
            if stats_container:
                stats['available'] = True
                
                # Extract each statistic
                stat_rows = stats_container.find_all('div', class_='stat-row')
                for row in stat_rows:
                    stat_name_elem = row.find('span', class_='stat-name')
                    if stat_name_elem:
                        stat_name = stat_name_elem.get_text(strip=True).lower()
                        
                        # Extract home and away values
                        home_value = self._extract_stat_value(row, 'home')
                        away_value = self._extract_stat_value(row, 'away')
                        
                        # Map to our statistics structure
                        if 'possession' in stat_name:
                            stats['possession'] = {'home': home_value, 'away': away_value}
                        elif 'shots' in stat_name and 'target' not in stat_name:
                            stats['shots'] = {'home': home_value, 'away': away_value}
                        elif 'shots on target' in stat_name:
                            stats['shots_on_target'] = {'home': home_value, 'away': away_value}
                        elif 'corner' in stat_name:
                            stats['corners'] = {'home': home_value, 'away': away_value}
                        elif 'foul' in stat_name:
                            stats['fouls'] = {'home': home_value, 'away': away_value}
                        elif 'yellow' in stat_name:
                            stats['yellow_cards'] = {'home': home_value, 'away': away_value}
                        elif 'red' in stat_name:
                            stats['red_cards'] = {'home': home_value, 'away': away_value}
                        elif 'offside' in stat_name:
                            stats['offsides'] = {'home': home_value, 'away': away_value}
            
            return stats
            
        except Exception as e:
            self.logger.warning(f"Error extracting detailed statistics: {str(e)}")
            return {'available': False}
    
    def _extract_stat_value(self, row_element, team: str) -> Optional[int]:
        """Extract statistic value for a specific team."""
        try:
            # Look for team-specific stat value
            team_class = f'{team}-stat' if team in ['home', 'away'] else 'stat-value'
            value_elem = row_element.find('span', class_=team_class)
            
            if not value_elem:
                # Try alternative selectors
                value_elems = row_element.find_all('span', class_='stat-value')
                if len(value_elems) >= 2:
                    value_elem = value_elems[0] if team == 'home' else value_elems[1]
            
            if value_elem:
                value_text = value_elem.get_text(strip=True)
                return self._parse_stat_number(value_text)
            
            return None
            
        except Exception:
            return None
    
    def _parse_stat_number(self, stat_text: str) -> Optional[int]:
        """Parse statistic number from text."""
        try:
            # Handle percentage values
            if '%' in stat_text:
                number_match = re.search(r'(\d+)%', stat_text)
                if number_match:
                    return int(number_match.group(1))
            
            # Handle regular numbers
            number_match = re.search(r'(\d+)', stat_text)
            if number_match:
                return int(number_match.group(1))
            
            return None
            
        except Exception:
            return None
    
    async def _extract_player_statistics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract individual player statistics."""
        try:
            player_stats = {
                'home_team': [],
                'away_team': [],
                'available': False
            }
            
            # Look for player statistics container
            players_container = soup.find('div', class_='player-statistics')
            if players_container:
                player_stats['available'] = True
                
                # Extract home team players
                home_players = players_container.find('div', class_='home-players')
                if home_players:
                    player_stats['home_team'] = self._extract_team_player_stats(home_players)
                
                # Extract away team players
                away_players = players_container.find('div', class_='away-players')
                if away_players:
                    player_stats['away_team'] = self._extract_team_player_stats(away_players)
            
            return player_stats
            
        except Exception as e:
            self.logger.warning(f"Error extracting player statistics: {str(e)}")
            return {'available': False}
    
    def _extract_team_player_stats(self, team_container) -> List[Dict[str, Any]]:
        """Extract player statistics for a team."""
        try:
            players = []
            player_elements = team_container.find_all('div', class_='player')
            
            for player_elem in player_elements:
                player_data = {
                    'name': None,
                    'position': None,
                    'rating': None,
                    'goals': 0,
                    'assists': 0,
                    'yellow_cards': 0,
                    'red_cards': 0
                }
                
                # Extract player name
                name_elem = player_elem.find('span', class_='player-name')
                if name_elem:
                    player_data['name'] = name_elem.get_text(strip=True)
                
                # Extract other player stats
                # This would need to be customized based on actual page structure
                
                if player_data['name']:
                    players.append(player_data)
            
            return players
            
        except Exception:
            return []
    
    async def _extract_match_summary(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract match summary and analysis."""
        try:
            summary = {
                'duration': None,
                'attendance': None,
                'referee': None,
                'venue': None,
                'weather_conditions': None,
                'match_report': None
            }
            
            # Extract match info
            info_container = soup.find('div', class_='match-info')
            if info_container:
                # Extract venue
                venue_elem = info_container.find('span', class_='venue')
                if venue_elem:
                    summary['venue'] = venue_elem.get_text(strip=True)
                
                # Extract referee
                referee_elem = info_container.find('span', class_='referee')
                if referee_elem:
                    summary['referee'] = referee_elem.get_text(strip=True)
                
                # Extract attendance
                attendance_elem = info_container.find('span', class_='attendance')
                if attendance_elem:
                    attendance_text = attendance_elem.get_text(strip=True)
                    attendance_match = re.search(r'([\d,]+)', attendance_text)
                    if attendance_match:
                        summary['attendance'] = int(attendance_match.group(1).replace(',', ''))
            
            return summary
            
        except Exception as e:
            self.logger.warning(f"Error extracting match summary: {str(e)}")
            return {}
    
    # Helper methods inherited from PreMatchExtractor:
    # - _extract_match_id()
    # - _extract_teams_info()
    # - _extract_team_logo()
    # - _extract_match_url()
    # - _extract_competition()
    
    def _extract_finished_match_time(self, element) -> Optional[str]:
        """Extract finished match time/date for completed matches."""
        try:
            # Use the inherited _extract_match_time method but with additional selectors for finished matches
            time_text = self._extract_match_time(element)
            if time_text:
                return time_text
            
            # Additional selectors specific to finished matches
            finished_time_selectors = [
                '.match-date',
                '.finished-time',
                '.result-time'
            ]
            
            for selector in finished_time_selectors:
                time_elem = element.select_one(selector)
                if time_elem:
                    time_text = time_elem.get_text(strip=True)
                    if time_text:
                        return time_text
            
            return None
        except Exception:
            return None
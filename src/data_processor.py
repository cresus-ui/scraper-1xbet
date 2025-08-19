"""Data processor with Pydantic validation for 1xbet scraper.

This module handles data processing, validation, transformation and export
of scraped data using Pydantic models for type safety and validation.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field, validator, ValidationError
from enum import Enum

from .config import ScrapingConfig


class MatchStatus(str, Enum):
    """Match status enumeration."""
    UPCOMING = "upcoming"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    """Match event type enumeration."""
    GOAL = "goal"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    SUBSTITUTION = "substitution"
    PENALTY = "penalty"
    OWN_GOAL = "own_goal"
    OFFSIDE = "offside"
    CORNER = "corner"
    FREE_KICK = "free_kick"


class TeamInfo(BaseModel):
    """Team information model."""
    name: str = Field(..., min_length=1, description="Team name")
    logo_url: Optional[str] = Field(None, description="Team logo URL")
    country: Optional[str] = Field(None, description="Team country")
    ranking: Optional[int] = Field(None, ge=1, description="Team ranking")
    
    @validator('logo_url')
    def validate_logo_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Logo URL must be a valid HTTP/HTTPS URL')
        return v


class OddsData(BaseModel):
    """Betting odds model."""
    home_win: Optional[float] = Field(None, gt=0, description="Home team win odds")
    draw: Optional[float] = Field(None, gt=0, description="Draw odds")
    away_win: Optional[float] = Field(None, gt=0, description="Away team win odds")
    over_under: Optional[Dict[str, float]] = Field(None, description="Over/Under odds")
    both_teams_score: Optional[Dict[str, float]] = Field(None, description="Both teams to score odds")
    handicap: Optional[Dict[str, float]] = Field(None, description="Handicap odds")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WeatherData(BaseModel):
    """Weather information model."""
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity: Optional[float] = Field(None, ge=0, le=100, description="Humidity percentage")
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed in km/h")
    conditions: Optional[str] = Field(None, description="Weather conditions")
    precipitation: Optional[float] = Field(None, ge=0, description="Precipitation in mm")


class PlayerInfo(BaseModel):
    """Player information model."""
    name: str = Field(..., min_length=1, description="Player name")
    position: Optional[str] = Field(None, description="Player position")
    number: Optional[int] = Field(None, ge=1, le=99, description="Jersey number")
    age: Optional[int] = Field(None, ge=16, le=50, description="Player age")
    nationality: Optional[str] = Field(None, description="Player nationality")


class LineupData(BaseModel):
    """Team lineup model."""
    formation: Optional[str] = Field(None, description="Team formation")
    starting_eleven: List[PlayerInfo] = Field(default_factory=list, description="Starting eleven players")
    substitutes: List[PlayerInfo] = Field(default_factory=list, description="Substitute players")
    coach: Optional[str] = Field(None, description="Coach name")


class ScoreData(BaseModel):
    """Score information model."""
    home_score: int = Field(..., ge=0, description="Home team score")
    away_score: int = Field(..., ge=0, description="Away team score")
    raw_score: Optional[str] = Field(None, description="Raw score text")


class MatchEvent(BaseModel):
    """Match event model."""
    minute: Optional[str] = Field(None, description="Event minute")
    type: Optional[EventType] = Field(None, description="Event type")
    player: Optional[str] = Field(None, description="Player involved")
    team: Optional[str] = Field(None, description="Team involved")
    description: str = Field(..., min_length=1, description="Event description")


class MatchStatistics(BaseModel):
    """Match statistics model."""
    possession: Optional[Dict[str, int]] = Field(None, description="Ball possession percentage")
    shots: Optional[Dict[str, int]] = Field(None, description="Total shots")
    shots_on_target: Optional[Dict[str, int]] = Field(None, description="Shots on target")
    passes: Optional[Dict[str, int]] = Field(None, description="Total passes")
    pass_accuracy: Optional[Dict[str, float]] = Field(None, description="Pass accuracy percentage")
    fouls: Optional[Dict[str, int]] = Field(None, description="Total fouls")
    corners: Optional[Dict[str, int]] = Field(None, description="Corner kicks")
    offsides: Optional[Dict[str, int]] = Field(None, description="Offsides")
    yellow_cards: Optional[Dict[str, int]] = Field(None, description="Yellow cards")
    red_cards: Optional[Dict[str, int]] = Field(None, description="Red cards")
    available: bool = Field(default=False, description="Statistics availability")


class PlayerStatistics(BaseModel):
    """Player statistics model."""
    name: str = Field(..., min_length=1, description="Player name")
    position: Optional[str] = Field(None, description="Player position")
    rating: Optional[float] = Field(None, ge=0, le=10, description="Player rating")
    goals: int = Field(default=0, ge=0, description="Goals scored")
    assists: int = Field(default=0, ge=0, description="Assists")
    yellow_cards: int = Field(default=0, ge=0, description="Yellow cards")
    red_cards: int = Field(default=0, ge=0, description="Red cards")
    minutes_played: Optional[int] = Field(None, ge=0, le=120, description="Minutes played")
    shots: Optional[int] = Field(None, ge=0, description="Shots taken")
    passes: Optional[int] = Field(None, ge=0, description="Passes made")
    pass_accuracy: Optional[float] = Field(None, ge=0, le=100, description="Pass accuracy")


class MatchData(BaseModel):
    """Complete match data model."""
    match_id: str = Field(..., min_length=1, description="Unique match identifier")
    sport: str = Field(..., min_length=1, description="Sport type")
    competition: Optional[str] = Field(None, description="Competition/League name")
    status: MatchStatus = Field(..., description="Match status")
    
    # Team information
    teams: Dict[str, TeamInfo] = Field(..., description="Home and away team info")
    
    # Match timing
    match_time: Optional[str] = Field(None, description="Match date/time")
    match_url: Optional[str] = Field(None, description="Match detail URL")
    
    # Pre-match data
    odds: Optional[OddsData] = Field(None, description="Betting odds")
    weather: Optional[WeatherData] = Field(None, description="Weather conditions")
    lineups: Optional[Dict[str, LineupData]] = Field(None, description="Team lineups")
    
    # Post-match data
    final_score: Optional[Union[ScoreData, Dict[str, Any]]] = Field(None, description="Final score")
    half_time_score: Optional[Union[ScoreData, Dict[str, Any]]] = Field(None, description="Half-time score")
    events: List[MatchEvent] = Field(default_factory=list, description="Match events")
    statistics: Optional[MatchStatistics] = Field(None, description="Match statistics")
    player_statistics: Optional[Dict[str, List[PlayerStatistics]]] = Field(None, description="Player statistics")
    
    # Metadata
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_source: str = Field(default="1xbet.com", description="Data source")
    
    @validator('teams')
    def validate_teams(cls, v):
        required_keys = {'home_team', 'away_team'}
        if not required_keys.issubset(v.keys()):
            raise ValueError('Teams must contain home_team and away_team')
        return v
    
    @validator('match_url')
    def validate_match_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Match URL must be a valid HTTP/HTTPS URL')
        return v


class ScrapingResult(BaseModel):
    """Scraping result model."""
    success: bool = Field(..., description="Scraping success status")
    total_matches: int = Field(..., ge=0, description="Total matches processed")
    successful_extractions: int = Field(..., ge=0, description="Successful extractions")
    failed_extractions: int = Field(..., ge=0, description="Failed extractions")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    execution_time: float = Field(..., ge=0, description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @validator('successful_extractions', 'failed_extractions')
    def validate_extraction_counts(cls, v, values):
        if 'total_matches' in values and v > values['total_matches']:
            raise ValueError('Extraction count cannot exceed total matches')
        return v


class DataProcessor:
    """Data processor with Pydantic validation."""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.processed_matches: List[MatchData] = []
        self.validation_errors: List[str] = []
    
    def process_raw_match_data(self, raw_data: Dict[str, Any]) -> Optional[MatchData]:
        """Process and validate raw match data."""
        try:
            # Clean and transform raw data
            cleaned_data = self._clean_raw_data(raw_data)
            
            # Validate with Pydantic
            match_data = MatchData(**cleaned_data)
            
            # Additional processing
            match_data = self._enrich_match_data(match_data)
            
            self.processed_matches.append(match_data)
            self.logger.info(f"Successfully processed match: {match_data.match_id}")
            
            return match_data
            
        except ValidationError as e:
            error_msg = f"Validation error for match {raw_data.get('match_id', 'unknown')}: {str(e)}"
            self.logger.error(error_msg)
            self.validation_errors.append(error_msg)
            return None
        
        except Exception as e:
            error_msg = f"Processing error for match {raw_data.get('match_id', 'unknown')}: {str(e)}"
            self.logger.error(error_msg)
            self.validation_errors.append(error_msg)
            return None
    
    def _clean_raw_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize raw data."""
        cleaned = raw_data.copy()
        
        # Ensure required fields exist
        if 'match_id' not in cleaned or not cleaned['match_id']:
            cleaned['match_id'] = f"match_{hash(str(raw_data)) % 1000000}"
        
        if 'sport' not in cleaned:
            cleaned['sport'] = 'unknown'
        
        if 'status' not in cleaned:
            cleaned['status'] = MatchStatus.UPCOMING
        
        # Clean teams data
        if 'teams' in cleaned:
            cleaned['teams'] = self._clean_teams_data(cleaned['teams'])
        
        # Clean odds data
        if 'odds' in cleaned and cleaned['odds']:
            cleaned['odds'] = self._clean_odds_data(cleaned['odds'])
        
        # Clean weather data
        if 'weather' in cleaned and cleaned['weather']:
            cleaned['weather'] = self._clean_weather_data(cleaned['weather'])
        
        # Clean events data
        if 'events' in cleaned and cleaned['events']:
            cleaned['events'] = self._clean_events_data(cleaned['events'])
        
        # Clean statistics data
        if 'statistics' in cleaned and cleaned['statistics']:
            cleaned['statistics'] = self._clean_statistics_data(cleaned['statistics'])
        
        return cleaned
    
    def _clean_teams_data(self, teams_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean teams data."""
        cleaned_teams = {}
        
        for team_key in ['home_team', 'away_team']:
            if team_key in teams_data:
                team_info = teams_data[team_key]
                if isinstance(team_info, dict):
                    cleaned_teams[team_key] = {
                        'name': str(team_info.get('name', 'Unknown')),
                        'logo_url': team_info.get('logo_url'),
                        'country': team_info.get('country'),
                        'ranking': team_info.get('ranking')
                    }
                elif isinstance(team_info, str):
                    cleaned_teams[team_key] = {
                        'name': team_info,
                        'logo_url': None,
                        'country': None,
                        'ranking': None
                    }
        
        return cleaned_teams
    
    def _clean_odds_data(self, odds_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean odds data."""
        cleaned_odds = {}
        
        # Clean numeric odds
        for key in ['home_win', 'draw', 'away_win']:
            if key in odds_data:
                try:
                    value = float(odds_data[key])
                    if value > 0:
                        cleaned_odds[key] = value
                except (ValueError, TypeError):
                    pass
        
        # Clean complex odds (over/under, etc.)
        for key in ['over_under', 'both_teams_score', 'handicap']:
            if key in odds_data and isinstance(odds_data[key], dict):
                cleaned_odds[key] = odds_data[key]
        
        return cleaned_odds
    
    def _clean_weather_data(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean weather data."""
        cleaned_weather = {}
        
        # Clean numeric weather values
        numeric_fields = ['temperature', 'humidity', 'wind_speed', 'precipitation']
        for field in numeric_fields:
            if field in weather_data:
                try:
                    value = float(weather_data[field])
                    cleaned_weather[field] = value
                except (ValueError, TypeError):
                    pass
        
        # Clean text fields
        if 'conditions' in weather_data:
            cleaned_weather['conditions'] = str(weather_data['conditions'])
        
        return cleaned_weather
    
    def _clean_events_data(self, events_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean match events data."""
        cleaned_events = []
        
        for event in events_data:
            if isinstance(event, dict) and 'description' in event:
                cleaned_event = {
                    'minute': event.get('minute'),
                    'type': event.get('type'),
                    'player': event.get('player'),
                    'team': event.get('team'),
                    'description': str(event['description'])
                }
                cleaned_events.append(cleaned_event)
        
        return cleaned_events
    
    def _clean_statistics_data(self, stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean statistics data."""
        cleaned_stats = {'available': stats_data.get('available', False)}
        
        # Clean team-based statistics
        stat_fields = ['possession', 'shots', 'shots_on_target', 'passes', 'fouls', 'corners', 'offsides']
        
        for field in stat_fields:
            if field in stats_data and isinstance(stats_data[field], dict):
                cleaned_field = {}
                for team_key in ['home', 'away']:
                    if team_key in stats_data[field]:
                        try:
                            value = int(stats_data[field][team_key])
                            cleaned_field[team_key] = value
                        except (ValueError, TypeError):
                            pass
                
                if cleaned_field:
                    cleaned_stats[field] = cleaned_field
        
        return cleaned_stats
    
    def _enrich_match_data(self, match_data: MatchData) -> MatchData:
        """Enrich match data with additional processing."""
        # Add derived fields or calculations
        # This could include calculating total goals, match duration, etc.
        
        return match_data
    
    def process_batch(self, raw_matches: List[Dict[str, Any]]) -> List[MatchData]:
        """Process a batch of raw match data."""
        processed_matches = []
        
        for raw_match in raw_matches:
            processed_match = self.process_raw_match_data(raw_match)
            if processed_match:
                processed_matches.append(processed_match)
        
        self.logger.info(f"Processed {len(processed_matches)} out of {len(raw_matches)} matches")
        return processed_matches
    
    def export_to_json(self, matches: List[MatchData], output_path: str) -> bool:
        """Export processed matches to JSON file."""
        try:
            # Convert Pydantic models to dictionaries
            matches_dict = [match.dict() for match in matches]
            
            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(matches_dict, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Exported {len(matches)} matches to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to JSON: {str(e)}")
            return False
    
    def export_to_csv(self, matches: List[MatchData], output_path: str) -> bool:
        """Export processed matches to CSV file."""
        try:
            import pandas as pd
            
            # Flatten match data for CSV export
            flattened_data = []
            
            for match in matches:
                flat_match = {
                    'match_id': match.match_id,
                    'sport': match.sport,
                    'competition': match.competition,
                    'status': match.status,
                    'home_team': match.teams.get('home_team', {}).get('name'),
                    'away_team': match.teams.get('away_team', {}).get('name'),
                    'match_time': match.match_time,
                    'match_url': match.match_url,
                    'extracted_at': match.extracted_at
                }
                
                # Add odds if available
                if match.odds:
                    flat_match.update({
                        'home_win_odds': match.odds.home_win,
                        'draw_odds': match.odds.draw,
                        'away_win_odds': match.odds.away_win
                    })
                
                # Add scores if available
                if match.final_score:
                    if isinstance(match.final_score, dict):
                        flat_match.update({
                            'home_score': match.final_score.get('home_score'),
                            'away_score': match.final_score.get('away_score')
                        })
                
                flattened_data.append(flat_match)
            
            # Create DataFrame and export
            df = pd.DataFrame(flattened_data)
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            self.logger.info(f"Exported {len(matches)} matches to {output_path}")
            return True
            
        except ImportError:
            self.logger.error("pandas is required for CSV export")
            return False
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {str(e)}")
            return False
    
    def get_processing_summary(self) -> ScrapingResult:
        """Get processing summary."""
        total_processed = len(self.processed_matches)
        total_errors = len(self.validation_errors)
        
        return ScrapingResult(
            success=total_errors == 0,
            total_matches=total_processed + total_errors,
            successful_extractions=total_processed,
            failed_extractions=total_errors,
            errors=self.validation_errors,
            execution_time=0.0,  # This would be calculated by the main processor
            timestamp=datetime.now(timezone.utc)
        )
    
    def reset(self):
        """Reset processor state."""
        self.processed_matches.clear()
        self.validation_errors.clear()
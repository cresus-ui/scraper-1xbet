"""Module defines the main entry point for the 1xBet Sports Data Scraper.

This Actor scrapes sports data from 1xbet.com including match information,
statistics, odds, lineups, and weather data for various sports.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any

from apify import Actor
from config import ConfigManager
from session_manager import SessionManager
from data_processor import DataProcessor
from monitoring import ScrapingMonitor
from extractors.prematch_extractor import PreMatchExtractor
from extractors.postmatch_extractor import PostMatchExtractor


async def main() -> None:
    """Main entry point for the 1xBet Sports Data Scraper.
    
    This coroutine handles the complete scraping workflow:
    1. Load and validate configuration
    2. Initialize session and extractors
    3. Extract data for each sport
    4. Process and save results
    5. Generate monitoring reports
    """
    async with Actor:
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)
        
        try:
            # Load configuration
            logger.info("Initializing 1xBet Sports Data Scraper...")
            config_manager = ConfigManager()
            config = await config_manager.load_config()
            
            logger.info(f"Configuration loaded successfully for sports: {config.sports}")
            
            # Initialize components
            session_manager = SessionManager(config_manager)
            data_processor = DataProcessor(config)
            monitoring = ScrapingMonitor(config.__dict__)
            
            # Start monitoring
            monitoring.track_memory_usage()
            
            # Initialize extractors
            prematch_extractor = None
            postmatch_extractor = None
            
            if config.include_pre_match:
                prematch_extractor = PreMatchExtractor(session_manager, config)
                logger.info("Pre-match extractor initialized")
            
            if config.include_post_match:
                postmatch_extractor = PostMatchExtractor(session_manager, config)
                logger.info("Post-match extractor initialized")
            
            # Start browser session
            await session_manager.start_session()
            logger.info("Browser session started")
            
            # Process each sport
            all_results = []
            base_urls = config_manager.get_base_urls()
            
            for sport in config.sports:
                logger.info(f"Starting extraction for sport: {sport}")
                
                try:
                    sport_results = await extract_sport_data(
                        sport=sport,
                        base_url=base_urls.get(sport),
                        prematch_extractor=prematch_extractor,
                        postmatch_extractor=postmatch_extractor,
                        config=config,
                        monitoring=monitoring
                    )
                    
                    # Process and validate data using process_batch
                    processed_results = await data_processor.process_batch(sport_results)
                    
                    all_results.extend(processed_results)
                    
                    logger.info(
                        f"Completed extraction for {sport}: {len(processed_results)} matches"
                    )
                    
                except Exception as e:
                    logger.error(f"Error extracting data for {sport}: {str(e)}")
                    monitoring.record_error(
                        monitoring._classify_error(e), 
                        f"Error extracting data for {sport}: {str(e)}"
                    )
                    continue
            
            # Save results to Apify dataset
            if all_results:
                await Actor.push_data(all_results)
                logger.info(f"Saved {len(all_results)} total records to dataset")
            else:
                logger.warning("No data extracted")
            
            # Generate final monitoring report
            monitoring.finalize_metrics()
            monitoring_report = monitoring.get_performance_summary()
            
            # Save monitoring report as separate dataset entry
            await Actor.push_data({
                "_type": "monitoring_report",
                "report": monitoring_report,
                "timestamp": monitoring_report.get("session_end")
            })
            
            logger.info("Scraping completed successfully")
            
        except Exception as e:
            logger.error(f"Fatal error in main execution: {str(e)}")
            # Save error information
            await Actor.push_data({
                "_type": "error_report",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            })
            raise


async def extract_sport_data(
    sport: str,
    base_url: str,
    prematch_extractor: PreMatchExtractor,
    postmatch_extractor: PostMatchExtractor,
    config,
    monitoring: ScrapingMonitor
) -> List[Dict[str, Any]]:
    """Extract data for a specific sport.
    
    Args:
        sport: Sport name
        base_url: Base URL for the sport
        prematch_extractor: Pre-match data extractor
        postmatch_extractor: Post-match data extractor
        config: Scraping configuration
        monitoring: Monitoring manager
        
    Returns:
        List of extracted match data
    """
    logger = logging.getLogger(__name__)
    results = []
    
    if not base_url:
        logger.warning(f"No base URL configured for sport: {sport}")
        return results
    
    try:
        # Extract pre-match data
        if prematch_extractor and config.include_pre_match:
            logger.info(f"Extracting pre-match data for {sport}")
            prematch_data = await prematch_extractor.extract_matches_list(
                sport=sport,
                page_url=base_url
            )
            results.extend(prematch_data)
            monitoring.track_match_extraction(f"{sport}_prematch", True, len(str(prematch_data)))
        
        # Extract post-match data
        if postmatch_extractor and config.include_post_match:
            logger.info(f"Extracting post-match data for {sport}")
            postmatch_data = await postmatch_extractor.extract_finished_matches(
                sport=sport,
                page_url=base_url
            )
            results.extend(postmatch_data)
            monitoring.track_match_extraction(f"{sport}_postmatch", True, len(str(postmatch_data)))
        
        # Add delay between sports
        if config.delay_between_requests > 0:
            await asyncio.sleep(config.delay_between_requests)
        
    except Exception as e:
        logger.error(f"Error extracting data for {sport}: {str(e)}")
        raise
    
    return results


if __name__ == "__main__":
    asyncio.run(main())

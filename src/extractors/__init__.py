"""Extractors package for 1xbet scraper.

This package contains modules for extracting different types of data
from 1xbet.com including pre-match and post-match data.
"""

from extractors.prematch_extractor import PreMatchExtractor
from extractors.postmatch_extractor import PostMatchExtractor

__all__ = ['PreMatchExtractor', 'PostMatchExtractor']
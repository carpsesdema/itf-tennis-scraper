"""
SofaScore scraper implementation for ITF tennis matches.
"""

import asyncio
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import aiohttp

from .base import BaseScraper
from ..core.models import TennisMatch, ScrapingResult, MatchStatus, TournamentLevel


class SofascoreScraper(BaseScraper):
    """Scraper for SofaScore ITF tennis matches."""

    BASE_URL = "https://www.sofascore.com"
    API_BASE = "https://api.sofascore.com/api/v1"

    # Tournament IDs for ITF categories
    ITF_TOURNAMENT_IDS = {
        "men": [
            23776,  # ITF Men
            23777,  # ITF Men M15
            23778,  # ITF Men M25
        ],
        "women": [
            23780,  # ITF Women
            23781,  # ITF Women W15
            23782,  # ITF Women W25
        ]
    }

    async def get_source_name(self) -> str:
        """Return the name of this scraping source."""
        return "sofascore"

    async def is_available(self) -> bool:
        """Check if SofaScore is currently available."""
        return await self._check_site_availability(self.BASE_URL)

    async def scrape_matches(self) -> ScrapingResult:
        """Scrape ITF matches from SofaScore."""
        start_time = datetime.now()
        all_matches = []

        try:
            self.logger.info("Starting SofaScore scraping...")

            # Scrape both men's and women's tournaments
            men_matches = await self._scrape_category("men")
            women_matches = await self._scrape_category("women")

            all_matches.extend(men_matches)
            all_matches.extend(women_matches)

            duration = (datetime.now() - start_time).total_seconds()

            return ScrapingResult(
                matches=all_matches,
                source=await self.get_source_name(),
                timestamp=datetime.now(),
                success=True,
                metadata={
                    'men_matches': len(men_matches),
                    'women_matches': len(women_matches),
                    'duration_seconds': duration,
                    'api_calls': len(self.ITF_TOURNAMENT_IDS["men"]) + len(self.ITF_TOURNAMENT_IDS["women"])
                }
            )

        except Exception as e:
            self.logger.error(f"SofaScore scraping failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()

            return ScrapingResult(
                matches=all_matches,
                source=await self.get_source_name(),
                timestamp=datetime.now(),
                success=False,
                error_message=str(e),
                metadata={'duration_seconds': duration}
            )

    async def _scrape_category(self, category: str) -> List[TennisMatch]:
        """Scrape matches from a specific category."""
        matches = []
        tournament_ids = self.ITF_TOURNAMENT_IDS.get(category, [])

        self.logger.info(f"Scraping SofaScore {category} tournaments: {tournament_ids}")

        for tournament_id in tournament_ids:
            try:
                tournament_matches = await self._scrape_tournament(tournament_id, category)
                matches.extend(tournament_matches)

                # Add delay between tournament requests
                await asyncio.sleep(self.delay_between_requests)

            except Exception as e:
                self.logger.warning(f"Failed to scrape tournament {tournament_id}: {e}")

        self.logger.info(f"Found {len(matches)} matches for {category}")
        return matches

    async def _scrape_tournament(self, tournament_id: int, category: str) -> List[TennisMatch]:
        """Scrape matches from a specific tournament."""
        matches = []

        try:
            # Get tournament events (current/recent matches)
            events_url = f"{self.API_BASE}/sport/5/tournament/{tournament_id}/events/last/0"

            session = await self._get_session()
            async with session.get(events_url) as response:
                if response.status != 200:
                    self.logger.warning(f"API returned status {response.status} for tournament {tournament_id}")
                    return matches

                data = await response.json()
                events = data.get('events', [])

                self.logger.debug(f"Found {len(events)} events for tournament {tournament_id}")

                for event in events:
                    try:
                        match = await self._parse_event_data(event, category, tournament_id)
                        if match:
                            matches.append(match)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse event: {e}")

        except Exception as e:
            self.logger.error(f"Failed to scrape tournament {tournament_id}: {e}")

        return matches

    async def _parse_event_data(self, event: Dict[str, Any], category: str, tournament_id: int) -> Optional[
        TennisMatch]:
        """Parse event data into TennisMatch object."""
        try:
            # Extract basic match information
            home_team = event.get('homeTeam', {})
            away_team = event.get('awayTeam', {})

            home_player = home_team.get('name', '')
            away_player = away_team.get('name', '')

            if not home_player or not away_player:
                return None

            # Parse status
            status_data = event.get('status', {})
            status_code = status_data.get('code', 0)
            status_type = status_data.get('type', 'notstarted')

            match_status = self._parse_status(status_code, status_type)

            # Parse score
            score_data = event.get('homeScore', {}), event.get('awayScore', {})
            score_text = self._parse_score(score_data, match_status)

            # Tournament information
            tournament_data = event.get('tournament', {})
            tournament_name = tournament_data.get('name', f'ITF {category.title()}')

            # Round information
            round_info = event.get('roundInfo', {}).get('name', '')

            # Get additional details
            start_timestamp = event.get('startTimestamp')
            start_time = None
            if start_timestamp:
                start_time = datetime.fromtimestamp(start_timestamp)

            # Build match URL
            event_id = event.get('id', '')
            match_url = f"{self.BASE_URL}/tennis/match/{event_id}" if event_id else ""

            # Create match object
            match = self._create_match(
                home_player=home_player,
                away_player=away_player,
                score=score_text,
                status=match_status.value,
                tournament=tournament_name,
                round_info=round_info,
                url=match_url,
                match_id=str(event_id),
                sofascore_tournament_id=tournament_id,
                category=category,
                start_timestamp=start_timestamp
            )

            # Set scheduled time if available
            if start_time:
                match.scheduled_time = start_time

            # Determine tournament level
            match.tournament_level = self._determine_tournament_level(tournament_name)

            return match

        except Exception as e:
            self.logger.warning(f"Failed to parse event data: {e}")
            return None

    def _parse_status(self, status_code: int, status_type: str) -> MatchStatus:
        """Parse SofaScore status into MatchStatus enum."""
        # SofaScore status codes mapping
        if status_type == 'inprogress':
            return MatchStatus.LIVE
        elif status_type == 'finished':
            return MatchStatus.FINISHED
        elif status_type == 'notstarted':
            return MatchStatus.SCHEDULED
        elif status_type == 'postponed':
            return MatchStatus.POSTPONED
        elif status_type == 'cancelled':
            return MatchStatus.CANCELLED
        elif status_type == 'walkover':
            return MatchStatus.WALKOVER
        else:
            # Default based on status code
            if status_code in [6, 7, 8, 9, 10, 11, 12, 31, 32]:  # In progress codes
                return MatchStatus.LIVE
            elif status_code in [3, 4, 5]:  # Finished codes
                return MatchStatus.FINISHED
            elif status_code == 1:  # Not started
                return MatchStatus.SCHEDULED
            else:
                return MatchStatus.SCHEDULED

    def _parse_score(self, score_data: tuple, status: MatchStatus) -> str:
        """Parse score data into readable format."""
        try:
            home_score, away_score = score_data

            if not home_score or not away_score:
                return ""

            # Get sets data
            home_periods = home_score.get('period1', 0), home_score.get('period2', 0), home_score.get('period3', 0)
            away_periods = away_score.get('period1', 0), away_score.get('period2', 0), away_score.get('period3', 0)

            # Build score string
            score_parts = []
            for i, (home_set, away_set) in enumerate(zip(home_periods, away_periods)):
                if home_set == 0 and away_set == 0:
                    break
                score_parts.append(f"{home_set}-{away_set}")

            if score_parts:
                return " ".join(score_parts)

            # Fall back to display scores if no periods
            home_display = home_score.get('display', 0)
            away_display = away_score.get('display', 0)

            if home_display or away_display:
                return f"{home_display}-{away_display}"

            return ""

        except Exception as e:
            self.logger.warning(f"Failed to parse score: {e}")
            return ""

    def _determine_tournament_level(self, tournament_name: str) -> TournamentLevel:
        """Determine tournament level from name."""
        name_lower = tournament_name.lower()

        if 'itf' in name_lower:
            if 'm15' in name_lower or 'w15' in name_lower or '15k' in name_lower:
                return TournamentLevel.ITF_15K
            elif 'm25' in name_lower or 'w25' in name_lower or '25k' in name_lower:
                return TournamentLevel.ITF_25K
            elif 'm40' in name_lower or 'w40' in name_lower or '40k' in name_lower:
                return TournamentLevel.ITF_40K
            elif 'm60' in name_lower or 'w60' in name_lower or '60k' in name_lower:
                return TournamentLevel.ITF_60K
            elif 'm80' in name_lower or 'w80' in name_lower or '80k' in name_lower:
                return TournamentLevel.ITF_80K
            elif 'm100' in name_lower or 'w100' in name_lower or '100k' in name_lower:
                return TournamentLevel.ITF_100K
            else:
                return TournamentLevel.ITF_25K  # Default ITF level

        elif 'challenger' in name_lower:
            return TournamentLevel.CHALLENGER
        elif 'atp' in name_lower:
            if '250' in name_lower:
                return TournamentLevel.ATP_250
            elif '500' in name_lower:
                return TournamentLevel.ATP_500
            elif '1000' in name_lower or 'masters' in name_lower:
                return TournamentLevel.ATP_1000
            else:
                return TournamentLevel.ATP_250
        elif any(
                gs in name_lower for gs in ['wimbledon', 'roland garros', 'french open', 'us open', 'australian open']):
            return TournamentLevel.GRAND_SLAM

        return TournamentLevel.UNKNOWN

    async def get_live_scores(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed live scores for a specific match."""
        try:
            url = f"{self.API_BASE}/event/{match_id}"

            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('event', {})

        except Exception as e:
            self.logger.error(f"Failed to get live scores for match {match_id}: {e}")

        return None

    async def get_tournament_info(self, tournament_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed tournament information."""
        try:
            url = f"{self.API_BASE}/tournament/{tournament_id}"

            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('tournament', {})

        except Exception as e:
            self.logger.error(f"Failed to get tournament info for {tournament_id}: {e}")

        return None

    async def search_tournaments(self, query: str) -> List[Dict[str, Any]]:
        """Search for tournaments by name."""
        try:
            url = f"{self.API_BASE}/search/tournaments"
            params = {'q': query, 'sport': 5}  # Sport 5 = Tennis

            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])

        except Exception as e:
            self.logger.error(f"Failed to search tournaments: {e}")

        return []

    def get_supported_tournament_categories(self) -> List[str]:
        """Get list of supported tournament categories."""
        return list(self.ITF_TOURNAMENT_IDS.keys())

    def add_tournament_id(self, category: str, tournament_id: int):
        """Add a new tournament ID to scrape."""
        if category in self.ITF_TOURNAMENT_IDS:
            if tournament_id not in self.ITF_TOURNAMENT_IDS[category]:
                self.ITF_TOURNAMENT_IDS[category].append(tournament_id)
                self.logger.info(f"Added tournament {tournament_id} to {category} category")

    def remove_tournament_id(self, category: str, tournament_id: int):
        """Remove a tournament ID from scraping."""
        if category in self.ITF_TOURNAMENT_IDS:
            if tournament_id in self.ITF_TOURNAMENT_IDS[category]:
                self.ITF_TOURNAMENT_IDS[category].remove(tournament_id)
                self.logger.info(f"Removed tournament {tournament_id} from {category} category")

    async def get_player_info(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed player information."""
        try:
            url = f"{self.API_BASE}/player/{player_id}"

            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('player', {})

        except Exception as e:
            self.logger.error(f"Failed to get player info for {player_id}: {e}")

        return None

    async def get_head_to_head(self, player1_id: str, player2_id: str) -> Optional[Dict[str, Any]]:
        """Get head-to-head statistics between two players."""
        try:
            url = f"{self.API_BASE}/player/{player1_id}/h2h/{player2_id}"

            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data

        except Exception as e:
            self.logger.error(f"Failed to get H2H for {player1_id} vs {player2_id}: {e}")

        return None
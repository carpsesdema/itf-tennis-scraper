"""
SofaScore scraper implementation for ITF tennis matches.
"""

import asyncio
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone  # Ensure timezone awareness
import aiohttp  # Keep for direct use if BaseScraper session is not suitable for all cases

from .base import BaseScraper  # Inherit from BaseScraper
from ..core.models import TennisMatch, Player, Score, ScrapingResult, MatchStatus, TournamentLevel, Surface


# Logger is inherited from BaseScraper


class SofascoreScraper(BaseScraper):
    """Scraper for SofaScore ITF tennis matches."""

    BASE_URL = "https://www.sofascore.com"
    API_BASE = "https://api.sofascore.com/api/v1"

    # Tournament IDs for ITF categories
    # These might need updating or a more dynamic discovery method
    ITF_TOURNAMENT_IDS = {
        "men": [
            # Common ITF Men categories, adjust as needed
            # UniqueTournament IDs can be found by inspecting network requests on Sofascore
            # when browsing ITF Men sections.
            # Example:
            # 23776,  # ITF Men (general or a specific series)
            # For specific M15, M25, you might need to find their uniqueTournament IDs.
            # These IDs can change, so a robust solution might involve discovering them.
            # Let's assume a few placeholder IDs for now if specific ones are not readily available.
            # These are illustrative. You'll need to find current, valid IDs.
            17655,  # Placeholder for ITF Men - M15 Example
            17656,  # Placeholder for ITF Men - M25 Example
        ],
        "women": [
            # Example:
            # 23780,  # ITF Women (general or a specific series)
            17657,  # Placeholder for ITF Women - W15 Example
            17658,  # Placeholder for ITF Women - W25 Example
        ]
    }

    async def get_source_name(self) -> str:
        """Return the name of this scraping source."""
        return "sofascore"

    async def is_available(self) -> bool:
        """Check if SofaScore is currently available."""
        return await self._check_site_availability(self.BASE_URL, timeout=self.request_timeout)

    async def scrape_matches(self) -> ScrapingResult:
        """Scrape ITF matches from SofaScore."""
        start_time_dt = datetime.now(timezone.utc)
        all_matches: List[TennisMatch] = []
        error_message = None
        success = False
        api_calls_count = 0

        try:
            self.logger.info("Starting SofaScore scraping...")

            men_matches = await self._scrape_category("men")
            api_calls_count += len(self.ITF_TOURNAMENT_IDS.get("men", []))
            all_matches.extend(men_matches)

            await asyncio.sleep(self.delay_between_requests)  # Delay between categories

            women_matches = await self._scrape_category("women")
            api_calls_count += len(self.ITF_TOURNAMENT_IDS.get("women", []))
            all_matches.extend(women_matches)

            success = True
            self.logger.info(f"SofaScore scraping completed. Found {len(all_matches)} total matches.")

        except Exception as e:
            self.logger.error(f"SofaScore scraping failed: {e}", exc_info=True)
            error_message = str(e)

        duration = (datetime.now(timezone.utc) - start_time_dt).total_seconds()
        return ScrapingResult(
            source=await self.get_source_name(),
            matches=all_matches,
            success=success,
            error_message=error_message,
            duration_seconds=duration,
            timestamp=datetime.now(timezone.utc),
            metadata={
                'api_calls': api_calls_count,
                'men_matches_found': len(men_matches) if 'men_matches' in locals() else 0,
                'women_matches_found': len(women_matches) if 'women_matches' in locals() else 0,
            }
        )

    async def _scrape_category(self, category: str) -> List[TennisMatch]:
        """Scrape matches from a specific category (men/women)."""
        matches_in_category: List[TennisMatch] = []
        tournament_ids = self.ITF_TOURNAMENT_IDS.get(category, [])

        if not tournament_ids:
            self.logger.warning(f"No tournament IDs configured for SofaScore category: {category}")
            return matches_in_category

        self.logger.info(f"Scraping SofaScore {category} tournaments: {tournament_ids}")

        for tournament_id in tournament_ids:
            try:
                # API endpoint for events in a tournament for a specific date (today)
                # Sofascore API might require a date; using today's date.
                # Or, it might have an endpoint for "live" or "scheduled" events.
                # This is a common pattern: /unique-tournament/{id}/events/live
                # Or for a date: /unique-tournament/{id}/events/date/{YYYY-MM-DD}
                # For simplicity, let's try fetching recent/scheduled events.
                # The endpoint /last/0 usually gives recent and upcoming.
                events_url = f"{self.API_BASE}/unique-tournament/{tournament_id}/events/last/0"

                session = await self._get_session()
                async with session.get(events_url, timeout=self.request_timeout) as response:
                    response.raise_for_status()  # Will raise an error for 4xx/5xx responses
                    data = await response.json()
                    events = data.get('events', [])
                    self.logger.debug(f"Fetched {len(events)} events for tournament ID {tournament_id} ({category}).")

                    for event_data in events:
                        match = self._parse_event_data(event_data, category, tournament_id)
                        if match:
                            matches_in_category.append(match)

                await asyncio.sleep(self.delay_between_requests)  # Delay between individual tournament API calls

            except aiohttp.ClientResponseError as e_http:
                self.logger.warning(
                    f"HTTP error scraping SofaScore tournament {tournament_id} ({category}): {e_http.status} {e_http.message}")
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout scraping SofaScore tournament {tournament_id} ({category}).")
            except Exception as e:
                self.logger.error(f"Failed to scrape SofaScore tournament {tournament_id} ({category}): {e}",
                                  exc_info=True)

        self.logger.info(f"Found {len(matches_in_category)} matches for SofaScore category: {category}")
        return matches_in_category

    def _parse_event_data(self, event: Dict[str, Any], category_type: str, tour_id: int) -> Optional[TennisMatch]:
        """Parse event data from Sofascore API into TennisMatch object."""
        try:
            home_team = event.get('homeTeam', {})
            away_team = event.get('awayTeam', {})

            home_player_name = self._parse_player_name(home_team.get('name', 'N/A'))
            away_player_name = self._parse_player_name(away_team.get('name', 'N/A'))

            if home_player_name == 'N/A' or away_player_name == 'N/A':
                self.logger.debug(f"Skipping event due to missing player name(s): {event.get('id')}")
                return None

            status_obj = event.get('status', {})
            status_code = status_obj.get('code')
            status_description = status_obj.get('description', '').lower()  # Use description for more context

            # Infer status more reliably
            match_status = MatchStatus.UNKNOWN
            if status_obj.get('type') == 'inprogress':
                match_status = MatchStatus.LIVE
            elif status_obj.get('type') == 'finished':
                match_status = MatchStatus.FINISHED
            elif status_obj.get('type') == 'notstarted':
                match_status = MatchStatus.SCHEDULED
            elif status_description:  # Fallback to description based parsing
                match_status = self._parse_match_status(status_description)

            home_score_data = event.get('homeScore', {})
            away_score_data = event.get('awayScore', {})

            sets_list = []
            for i in range(1, 6):  # Max 5 sets
                p_home = home_score_data.get(f'period{i}')
                p_away = away_score_data.get(f'period{i}')
                if p_home is not None and p_away is not None:  # Only add if both scores for set exist
                    sets_list.append((int(p_home), int(p_away)))
                else:  # Stop if a set is missing
                    break

            current_game_score = None
            if match_status == MatchStatus.LIVE:
                cg_home = home_score_data.get('current')  # Sofascore sometimes has 'current' for game points
                cg_away = away_score_data.get('current')
                if cg_home is not None and cg_away is not None:  # Ensure both exist
                    current_game_score = (str(cg_home), str(cg_away))

            score_obj = Score(sets=sets_list, current_game=current_game_score)

            tournament_info = event.get('tournament', {})
            season_info = event.get('season', {})
            round_info_obj = event.get('roundInfo', {})

            tournament_name = tournament_info.get('name', f"ITF {category_type.title()}")
            if season_info.get('name') and season_info.get('name') not in tournament_name:
                tournament_name += f" {season_info.get('year', '')}"

            round_name = round_info_obj.get('name', round_info_obj.get('round', ''))

            scheduled_ts = event.get('startTimestamp')
            scheduled_dt = datetime.fromtimestamp(scheduled_ts, timezone.utc) if scheduled_ts else None

            match_id_val = str(event.get('id'))
            source_url_val = f"{self.BASE_URL}/tennis/match/{match_id_val}" if match_id_val else None

            # Determine tournament level and surface (can be challenging without more specific API fields)
            tour_level = self._determine_tournament_level_sofascore(
                tournament_info.get('uniqueTournament', {}).get('name', tournament_name))
            # Surface info might be in uniqueTournament or tournament details, needs inspection
            surface_name = tournament_info.get('groundType', '').capitalize()
            surface_val = Surface.UNKNOWN
            if surface_name:
                try:
                    surface_val = Surface(surface_name)
                except ValueError:
                    if "hard" in surface_name.lower():
                        surface_val = Surface.HARD
                    elif "clay" in surface_name.lower():
                        surface_val = Surface.CLAY
                    elif "grass" in surface_name.lower():
                        surface_val = Surface.GRASS

            return TennisMatch(
                home_player=Player(name=home_player_name, player_id=str(home_team.get('id'))),
                away_player=Player(name=away_player_name, player_id=str(away_team.get('id'))),
                score=score_obj,
                status=match_status,
                tournament=tournament_name,
                tournament_level=tour_level,
                surface=surface_val,
                round_info=round_name,
                scheduled_time=scheduled_dt,
                source="sofascore",  # Not ideal, set explicitly
                source_url=source_url_val,
                match_id=match_id_val,
                last_updated=datetime.now(timezone.utc),
                metadata={
                    'sofascore_event_id': event.get('id'),
                    'sofascore_tournament_id': tournament_info.get('tournament', {}).get('id', tour_id),
                    'sofascore_category_id': tournament_info.get('category', {}).get('id'),
                    'has_live_odds': event.get('hasOdds', False)  # Example metadata
                }
            )
        except Exception as e:
            self.logger.warning(f"Error parsing SofaScore event data (ID: {event.get('id')}): {e}", exc_info=True)
            return None

    def _determine_tournament_level_sofascore(self, name: str) -> TournamentLevel:
        """Enhanced tournament level detection for Sofascore names."""
        name_lower = name.lower()
        if "itf" in name_lower:
            if any(s in name_lower for s in ["m15", "w15", "15k"]): return TournamentLevel.ITF_15K
            if any(s in name_lower for s in ["m25", "w25", "25k"]): return TournamentLevel.ITF_25K
            # Add other ITF levels like 40k, 60k, 80k, 100k if distinguishable
            return TournamentLevel.ITF_25K  # Default for ITF
        if "challenger" in name_lower: return TournamentLevel.CHALLENGER
        # Add ATP/WTA/Grand Slam detection if you expand scope
        return TournamentLevel.UNKNOWN

    async def cleanup(self):
        """Cleanup resources for SofascoreScraper."""
        self.logger.info("Cleaning up SofascoreScraper resources...")
        await super().cleanup()  # Important to call BaseScraper's cleanup for the session
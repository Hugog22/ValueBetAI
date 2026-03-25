from understatapi import UnderstatClient
from core.config import get_current_season

def get_laliga_historical_data(season: str | None = None):
    """
    Downloads deep statistical history (xG, xA) from LaLiga for a given season.
    Returns a list of match data dictionaries.
    """
    if season is None:
        season = str(get_current_season())
    with UnderstatClient() as understat:
        # Get all matches for the league in the given season
        match_data = understat.league(league="La_Liga").get_match_data(season=season)
        return match_data

def get_match_shots(match_id: str):
    """
    Downloads detailed shot statistics (xG per shot) for a specific match.
    """
    with UnderstatClient() as understat:
        shot_data = understat.match(match=match_id).get_shot_data()
        return shot_data

from db.session import SessionLocal
from db.models import Match, Odds
from core.match_evaluator import _evaluate_world_cup_match
from core.shared_predictor import world_cup_predictor
from datetime import datetime, timedelta

db = SessionLocal()
now = datetime.utcnow()
seven_days = now + timedelta(days=7)
upcoming = (
    db.query(Match)
    .join(Odds, (Odds.match_id == Match.id) & (Odds.market == "h2h"))
    .filter(Match.date >= now, Match.date <= seven_days)
    .order_by(Match.date.asc())
    .distinct()
    .all()
)
from core.cache_service import _get_worldcup_team_names
wc_teams = _get_worldcup_team_names()

for m in upcoming:
    if m.home_team.name in wc_teams or m.away_team.name in wc_teams:
        try:
            res = _evaluate_world_cup_match(m, world_cup_predictor, db)
            print(f"Match {m.home_team.name} vs {m.away_team.name}: evaluated -> {bool(res)}")
        except Exception as e:
            print(f"Error evaluating {m.home_team.name} vs {m.away_team.name}: {e}")


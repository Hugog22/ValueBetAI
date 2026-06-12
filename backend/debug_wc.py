import logging
from db.session import SessionLocal
from db.models import Match
from etl.world_cup_etl import sync_world_cup_odds

logging.basicConfig(level=logging.DEBUG)
db = SessionLocal()
print("Matches before:", db.query(Match).count())
sync_world_cup_odds()
print("Matches after:", db.query(Match).count())

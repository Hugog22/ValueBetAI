"""
shared_predictor.py
-------------------
Singleton accessors for both predictors:
  - predictor          : ValueBetPredictor  (club football — La Liga, Premier, Champions)
  - world_cup_predictor: WorldCupPredictor  (national teams — FIFA World Cup)

Both are lazy-loaded on first use.
"""

from models.predictor import ValueBetPredictor
from models.world_cup_predictor import WorldCupPredictor

predictor: ValueBetPredictor = ValueBetPredictor()
world_cup_predictor: WorldCupPredictor = WorldCupPredictor()

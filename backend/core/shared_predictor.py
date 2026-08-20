"""
shared_predictor.py
-------------------
Singleton accessor for the La Liga predictor.
Lazy-loaded on first use.
"""

from models.predictor import ValueBetPredictor

predictor: ValueBetPredictor = ValueBetPredictor()

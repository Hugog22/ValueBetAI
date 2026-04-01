import sys
import os

sys.path.insert(0, os.path.abspath('backend'))
from core.match_evaluator import _evaluate_match
from models.predictor import ValueBetPredictor

class MockTeam:
    def __init__(self, name):
        self.name = name

class MockMatch:
    def __init__(self, hid, a, b):
        self.id = hid
        self.home_team = MockTeam(a)
        self.away_team = MockTeam(b)

if __name__ == "__main__":
    predictor = ValueBetPredictor()
    predictor.load_model()
    
    from core.match_evaluator import _build_match_features

    m1 = MockMatch(1, "Mallorca", "Real Madrid")
    features = _build_match_features(m1)
    res1 = predictor.predict_match(features)
    
    # Print the probability output
    print(f"=== {m1.home_team.name} vs {m1.away_team.name} ===")
    print("Probabilities:", res1["probabilities"])

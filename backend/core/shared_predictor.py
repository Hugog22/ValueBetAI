import logging
from models.predictor import ValueBetPredictor

logger = logging.getLogger(__name__)

# Football predictor — covers La Liga, Premier League and Champions League
predictor = ValueBetPredictor()
predictor.load_model()

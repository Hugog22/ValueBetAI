import logging
from models.predictor import ValueBetPredictor
from models.nba_predictor import NBAPredictor

logger = logging.getLogger(__name__)

# Football predictor (La Liga + EPL + Champions League)
predictor = ValueBetPredictor()
predictor.load_model()

# NBA predictor — loads gracefully even if model files don't exist yet
nba_predictor = NBAPredictor()
nba_predictor.load_model()

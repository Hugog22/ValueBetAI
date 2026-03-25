from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    bets = relationship("Bet", back_populates="user")

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    api_football_id = Column(Integer, unique=True, index=True)

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    api_football_id = Column(Integer, unique=True, index=True, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    
    # Advanced stats
    home_xg = Column(Float, nullable=True)
    away_xg = Column(Float, nullable=True)
    home_possession = Column(Float, nullable=True)
    away_possession = Column(Float, nullable=True)
    home_shots_on_target = Column(Integer, nullable=True)
    away_shots_on_target = Column(Integer, nullable=True)

    status = Column(String) # "Not Started", "Finished", etc.

    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])

class Odds(Base):
    __tablename__ = "odds"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    bookmaker = Column(String) # e.g., "bet365"
    market = Column(String) # e.g., "h2h"
    
    home_odds = Column(Float)
    draw_odds = Column(Float)
    away_odds = Column(Float)

    is_superboost = Column(Boolean, default=False)

    match = relationship("Match")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    predicted_home_prob = Column(Float) # Expected Probability
    predicted_draw_prob = Column(Float)
    predicted_away_prob = Column(Float)
    
    fair_home_odds = Column(Float) # Translated from Prob
    fair_draw_odds = Column(Float)
    fair_away_odds = Column(Float)

    value_bet_flag = Column(Boolean, default=False)
    recommendation = Column(String, nullable=True)
    confidence_score = Column(Integer, nullable=True) # 1-10

    match = relationship("Match")

class MarketOdds(Base):
    __tablename__ = "market_odds"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    bookmaker = Column(String) # e.g., "bet365"
    market_key = Column(String) # e.g., "btts", "double_chance"
    outcome_name = Column(String) # e.g., "Yes", "Home/Draw"
    
    price = Column(Float)
    point = Column(Float, nullable=True) # For spreads/totals

    match = relationship("Match")

class OddsHistory(Base):
    __tablename__ = "odds_history"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    bookmaker = Column(String) # e.g., "pinnacle", "bet365"
    market = Column(String) # e.g., "h2h"
    
    home_odds = Column(Float)
    draw_odds = Column(Float)
    away_odds = Column(Float)

    match = relationship("Match")

class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Temporarily nullable for legacy bets
    match_id = Column(Integer, ForeignKey("matches.id"))
    placed_at = Column(DateTime, default=datetime.utcnow)
    
    bookmaker = Column(String)
    market = Column(String)
    selection = Column(String) # e.g., "Home", "Away", "Draw", "Over 2.5"
    odds_taken = Column(Float)
    stake = Column(Float)
    
    # Tracking fields
    status = Column(String, default="Pending") # "Pending", "Won", "Lost", "Void"
    clv = Column(Float, nullable=True) # Closing Line Value at the time of match start

    match = relationship("Match")
    user = relationship("User", back_populates="bets")

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
    bankroll = Column(Float, default=1000.0)
    is_admin = Column(Boolean, default=False)
    reset_token_hash = Column(String, nullable=True)
    
    # Stripe integration
    stripe_customer_id = Column(String, unique=True, index=True, nullable=True)
    subscription_status = Column(String, nullable=True) # e.g., 'active', 'canceled', 'past_due'
    subscription_end_date = Column(DateTime, nullable=True)

    bets = relationship("Bet", back_populates="user")

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    api_football_id = Column(Integer, unique=True, index=True)
    
    world_cup_stats = relationship("WorldCupTeamStats", back_populates="team", uselist=False)

class WorldCupTeamStats(Base):
    __tablename__ = "world_cup_team_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), unique=True)
    matches_played = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="world_cup_stats")



class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    api_football_id = Column(Integer, unique=True, index=True, nullable=True)
    sofascore_event_id = Column(Integer, unique=True, index=True, nullable=True)
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
    stage = Column(String, nullable=True) # e.g. "GROUP_STAGE", "ROUND_OF_16"

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

class MatchTeamStatistics(Base):
    __tablename__ = "match_team_statistics"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    is_home = Column(Boolean)
    
    possession_pct = Column(Float, nullable=True)
    xg = Column(Float, nullable=True)
    big_chances = Column(Integer, nullable=True)
    big_chances_scored = Column(Integer, nullable=True)
    big_chances_missed = Column(Integer, nullable=True)
    shots_total = Column(Integer, nullable=True)
    shots_on_target = Column(Integer, nullable=True)
    shots_off_target = Column(Integer, nullable=True)
    shots_blocked = Column(Integer, nullable=True)
    shots_inside_box = Column(Integer, nullable=True)
    shots_outside_box = Column(Integer, nullable=True)
    corners = Column(Integer, nullable=True)
    fouls = Column(Integer, nullable=True)
    passes_total = Column(Integer, nullable=True)
    passes_accurate = Column(Integer, nullable=True)
    final_third_entries = Column(Integer, nullable=True)
    tackles = Column(Integer, nullable=True)
    interceptions = Column(Integer, nullable=True)
    recoveries = Column(Integer, nullable=True)
    clearances = Column(Integer, nullable=True)
    goalkeeper_saves = Column(Integer, nullable=True)
    goals_prevented = Column(Float, nullable=True)
    yellow_cards = Column(Integer, nullable=True)
    duels_won_pct = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match")
    team = relationship("Team")


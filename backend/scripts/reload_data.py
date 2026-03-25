import sys
import os
from datetime import datetime
import logging

# Set python path to backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal, engine
from db.models import Match, Team, OddsHistory, MarketOdds, Odds, Prediction, Bet
from etl.odds_api import get_laliga_odds_all_markets, pick_best_bookmaker
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reload_data():
    db = SessionLocal()
    
    try:
        print("--- Forced Database Reload ---")
        
        # 1. Truncate tables (PostgreSQL specific CASCADE just in case)
        print("Emptying tables...")
        # Note: Order matters due to foreign keys if not using CASCADE
        db.execute(text("TRUNCATE TABLE bets, predictions, odds_history, market_odds, odds, matches, teams RESTART IDENTITY CASCADE"))
        db.commit()
        print("Tables truncated successfully.")

        # 2. Fetch data from The Odds API
        print("Fetching data from The Odds API...")
        raw_data = get_laliga_odds_all_markets(markets=["h2h", "totals", "spreads"])
        print(f"Retrieved {len(raw_data)} events from API.")

        # 3. Populate Teams and Matches
        stored_matches = 0
        for event in raw_data:
            home_name = event["home_team"]
            away_name = event["away_team"]
            
            # Ensure teams exist
            home_team = db.query(Team).filter(Team.name == home_name).first()
            if not home_team:
                home_team = Team(name=home_name)
                db.add(home_team)
                db.flush()
                
            away_team = db.query(Team).filter(Team.name == away_name).first()
            if not away_team:
                away_team = Team(name=away_name)
                db.add(away_team)
                db.flush()
            
            # Parse date
            match_date = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
            
            # Create Match
            # Use api_football_id to store the Odds API event ID for reference
            match = Match(
                api_football_id=None, # We'll leave this for Understat/Football-API later
                date=match_date,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                status="Not Started"
            )
            # We use an internal hack to store the Odds-API ID temporarily if needed, 
            # but let's just use the teams/date as the key for now.
            db.add(match)
            db.flush()
            
            # 4. Populate Odds History and Market Odds
            for bm in event.get("bookmakers", []):
                bm_key = bm["key"]
                for market in bm.get("markets", []):
                    mkt_key = market["key"]
                    
                    # Store in MarketOdds for Omni-Market
                    for outcome in market.get("outcomes", []):
                        m_odd = MarketOdds(
                            match_id=match.id,
                            bookmaker=bm_key,
                            market_key=mkt_key,
                            outcome_name=outcome["name"],
                            price=outcome["price"],
                            point=outcome.get("point")
                        )
                        db.add(m_odd)
                    
                    # Specifically for OddsHistory and Odds (Main markets)
                    if mkt_key == "h2h":
                        outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
                        # Logic to map team names to "home", "away", "draw"
                        home_price = outcomes.get(home_name)
                        away_price = outcomes.get(away_name)
                        draw_price = outcomes.get("Draw")
                        
                        if home_price and away_price:
                            # OddsHistory (Line Shopping)
                            history = OddsHistory(
                                match_id=match.id,
                                bookmaker=bm_key,
                                market="h2h",
                                home_odds=home_price,
                                draw_odds=draw_price or 0,
                                away_odds=away_price
                            )
                            db.add(history)
                            
                            # Odds (Main table used by _evaluate_match)
                            # Only store if it's the best bookmaker (simulated priority)
                            main_odd = Odds(
                                match_id=match.id,
                                bookmaker=bm_key,
                                market="h2h",
                                home_odds=home_price,
                                draw_odds=draw_price or 0,
                                away_odds=away_price
                            )
                            db.add(main_odd)

            stored_matches += 1
            if stored_matches % 10 == 0:
                print(f"✅ Successfully stored {stored_matches} matches...")

        db.commit()
        print(f"\nSUCCESS: Reload complete. {stored_matches} matches and associated odds loaded.")
        print(f"Total Teams: {db.query(Team).count()}")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR during reload: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reload_data()

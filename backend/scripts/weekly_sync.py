"""
weekly_sync.py
--------------
Ejecutado cada martes para sincronizar resultados, resolver apuestas pendientes,
actualizar bankrolls y re-entrenar la IA con los nuevos resultados.
"""
import sys
import os
import logging
from datetime import datetime
import subprocess

# Setup paths for importing from backend/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import SessionLocal
from db.models import Match, Bet, User
from etl.football_api import get_match_statistics
from core.config import settings
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

API_SPORTS_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-apisports-key": settings.API_SPORTS_KEY
}

def sync_results_and_bankroll():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Find matches that are past their date but still "Not Started" or similar
        pending_matches = db.query(Match).filter(
            Match.date <= now,
            Match.status != "Match Finished" # Could be "Finished" depending on parsing
        ).all()
        
        logger.info(f"Encontrados {len(pending_matches)} partidos pendientes de actualizar resultado.")

        with httpx.Client() as client:
            for match in pending_matches:
                if not match.api_football_id:
                    continue
                
                try:
                    url = f"{API_SPORTS_BASE_URL}/fixtures"
                    params = {"id": match.api_football_id}
                    resp = client.get(url, headers=HEADERS, params=params)
                    resp.raise_for_status()
                    data = resp.json().get('response', [])
                    
                    if not data:
                        continue
                        
                    fixture_info = data[0]
                    status_short = fixture_info["fixture"]["status"]["short"]
                    
                    if status_short in ["FT", "AET", "PEN"]:
                        goals_h = fixture_info["goals"]["home"]
                        goals_a = fixture_info["goals"]["away"]
                        
                        if goals_h is not None and goals_a is not None:
                            match.home_goals = int(goals_h)
                            match.away_goals = int(goals_a)
                            match.status = "Finished"
                            logger.info(f"Actualizado {match.id}: {match.home_team.name} {goals_h} - {goals_a} {match.away_team.name}")
                            
                            # Optional: fetch corners/stats here if we want to enrich historical data precisely!
                            # For now, training data might rely on fetch_historical_data, but here we just get results.
                except Exception as e:
                    logger.error(f"Error parseando resultado para partido {match.id}: {e}")

        db.commit()

        # Resolve Pending Bets based on Finished Matches
        pending_bets = db.query(Bet).join(Match).filter(
            Match.status == "Finished",
            Bet.status == "Pending"
        ).all()

        logger.info(f"Encontradas {len(pending_bets)} apuestas por liquidar.")

        for bet in pending_bets:
            m = bet.match
            hg = m.home_goals
            ag = m.away_goals
            
            if hg is None or ag is None:
                continue

            won = False
            if bet.market in ["1x2", "Victoria Local", "Empate", "Victoria Visitante"]:
                if bet.selection in ["home", "Victoria Local"] and hg > ag:
                    won = True
                elif bet.selection in ["draw", "Empate"] and hg == ag:
                    won = True
                elif bet.selection in ["away", "Victoria Visitante"] and hg < ag:
                    won = True
            elif bet.market in ["ou25", "Más de 2.5 Goles", "Menos de 2.5 Goles"]:
                total = hg + ag
                if bet.selection in ["over", "Más de 2.5 Goles"] and total > 2.5:
                    won = True
                elif bet.selection in ["under", "Menos de 2.5 Goles"] and total < 2.5:
                    won = True
            
            if won:
                bet.status = "Won"
                # Stake already deducted at bet placement — return stake + profit
                full_return = bet.stake * bet.odds_taken
                if bet.user:
                    bet.user.bankroll = (bet.user.bankroll or 0.0) + full_return
                    logger.info(f"  ✅ Bet {bet.id} WON — Return {full_return:.2f}€ → New bankroll: {bet.user.bankroll:.2f}€")
            else:
                bet.status = "Lost"
                # Stake already deducted at placement — nothing more to do
                if bet.user:
                    logger.info(f"  ❌ Bet {bet.id} LOST — Stake {bet.stake:.2f}€ already deducted")

        db.commit()
        logger.info("Bankroll actualizado exitosamente.")
        
    finally:
        db.close()

def trigger_ai_retraining():
    logger.info("Iniciando Pipeline de Retraining de IA Semanal...")
    try:
        # Fetch remaining historical matches stats to populate training dataset properly
        logger.info("Paso 1: fetch_historical_data (completando features de la jornada pasada)")
        subprocess.run(["python", os.path.join(os.path.dirname(__file__), "fetch_historical_data.py")], check=True)
        
        # Opcional: corners
        logger.info("Paso 2: fetch_corners_data")
        subprocess.run(["python", os.path.join(os.path.dirname(__file__), "fetch_corners_data.py")], check=False)
        
        # Train v2
        logger.info("Paso 3: train_model_v2.py")
        subprocess.run(["python", os.path.join(os.path.dirname(__file__), "train_model_v2.py")], check=True)
        logger.info("Entrenamiento Semanal completado.")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Fallo en la cadena de entrenamiento: {e}")

if __name__ == "__main__":
    logger.info("=== INICIO WEEKLY SYNC ===")
    sync_results_and_bankroll()
    trigger_ai_retraining()
    logger.info("=== FIN WEEKLY SYNC ===")

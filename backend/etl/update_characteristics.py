import logging
from datetime import datetime
from db.session import SessionLocal
from db.models import Team, Match, TeamCharacteristic

logger = logging.getLogger(__name__)

def update_team_characteristics():
    """
    Automates the calculation of TeamCharacteristic (offensive strength, defensive solidity, 
    momentum, motivation) based on the team's last 10 finished matches.
    """
    db = SessionLocal()
    updated_count = 0
    try:
        teams = db.query(Team).all()
        
        for team in teams:
            # Get last 10 matches
            # Solo partidos de la temporada 26/27 (agosto 2026 en adelante)
            from datetime import datetime
            matches = db.query(Match).filter(
                (Match.home_team_id == team.id) | (Match.away_team_id == team.id),
                Match.status == "Finished",
                Match.date >= datetime(2026, 8, 1)
            ).order_by(Match.date.desc()).limit(10).all()
            
            if not matches:
                offensive_strength = 5.0
                defensive_solidity = 5.0
                motivation = 5.0
                momentum = 5.0
            else:
                n = len(matches)
                pts = 0
                xg_for_sum = 0.0
                xg_ag_sum = 0.0
                
                last_match_won = False
                
                for i, m in enumerate(matches):
                    is_home = (m.home_team_id == team.id)
                    gf = m.home_goals if is_home else m.away_goals
                    ga = m.away_goals if is_home else m.home_goals
                    
                    xg_f = m.home_xg if is_home else m.away_xg
                    xg_a = m.away_xg if is_home else m.home_xg
                    
                    # Fallback to actual goals if xG is missing
                    xg_f = xg_f if xg_f is not None else (gf or 0)
                    xg_a = xg_a if xg_a is not None else (ga or 0)
                    
                    xg_for_sum += xg_f
                    xg_ag_sum += xg_a
                    
                    if gf > ga:
                        pts += 3
                        if i == 0:
                            last_match_won = True
                    elif gf == ga:
                        pts += 1
                        
                xg_for_avg = xg_for_sum / n
                xg_ag_avg = xg_ag_sum / n
                
                # Momentum: Points won vs Total possible points in recent matches, scaled to 10
                momentum = (pts / (n * 3)) * 10.0
                
                # Offensive Strength: scaled so an avg xG of 2.5 = 10.0
                offensive_strength = min(10.0, max(0.0, xg_for_avg * 4.0))
                
                # Defensive Solidity: scaled so an avg xGa of 0 = 10.0, xGa of 2.5 = 0.0
                defensive_solidity = min(10.0, max(0.0, 10.0 - (xg_ag_avg * 4.0)))
                
                # Motivation: Base on momentum but boost if they won their last match
                motivation = min(10.0, momentum + (1.5 if last_match_won else 0.0))
            
            char = db.query(TeamCharacteristic).filter(TeamCharacteristic.team_id == team.id).first()
            if not char:
                char = TeamCharacteristic(
                    team_id=team.id,
                    offensive_strength=round(offensive_strength, 2),
                    defensive_solidity=round(defensive_solidity, 2),
                    motivation=round(motivation, 2),
                    momentum=round(momentum, 2)
                )
                db.add(char)
            else:
                char.offensive_strength = round(offensive_strength, 2)
                char.defensive_solidity = round(defensive_solidity, 2)
                char.motivation = round(motivation, 2)
                char.momentum = round(momentum, 2)
                char.updated_at = datetime.utcnow()
                
            updated_count += 1
            
        db.commit()
        logger.info(f"✅ Auto-updated characteristics for {updated_count} teams.")
    except Exception as e:
        logger.error(f"❌ Error updating team characteristics: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_team_characteristics()

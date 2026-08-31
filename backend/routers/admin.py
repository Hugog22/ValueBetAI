from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import os, json
try:
    from zoneinfo import ZoneInfo
    MADRID_TZ = ZoneInfo("Europe/Madrid")
except ImportError:
    MADRID_TZ = None

def format_trained_at(ts: str) -> str:
    if not ts or ts == "N/A": return "N/A"
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        if MADRID_TZ:
            dt = dt.astimezone(MADRID_TZ)
        return dt.strftime("%Y-%m-%d %H:%M:%S (Madrid)")
    except Exception:
        return ts

from db.session import get_db
from db.models import Bet, Match, User, Team, MatchTeamStatistics, TeamCharacteristic
from routers.auth import get_current_user

ADMIN_EMAIL = "hugodesax123@gmail.com"

router = APIRouter(prefix="/api/admin", tags=["admin"])

class SystemStatsResponse(BaseModel):
    total_predictions: int
    won_predictions: int
    lost_predictions: int
    hit_rate: float
    hypothetical_yield: float
    total_users: int

class PredictionDetail(BaseModel):
    bet_id: int
    match_date: str
    home_team: str
    away_team: str
    market: str
    selection: str
    odds_taken: float
    stake: float
    status: str
    pnl: float
    user_email: str
    risk_level: Optional[str] = None
    risk_badge: Optional[str] = None
    risk_bg_class: Optional[str] = None

class PredictionsDetailResponse(BaseModel):
    period_days: int
    total: int
    won: int
    lost: int
    pending: int
    hit_rate: float
    total_staked: float
    net_pnl: float
    yield_percent: float
    predictions: List[PredictionDetail]

@router.get("/system-stats", response_model=SystemStatsResponse)
def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns global system performance based on the AI's predictions
    vs actual finished match results. Only accessible to the admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    all_bets = (
        db.query(Bet, Match)
        .join(Match, Bet.match_id == Match.id)
        .filter(Bet.status.in_(["Won", "Lost"]))
        .filter(Bet.user_id == None)
        .all()
    )

    # Deduplicate legacy merged bets or multiple clicks across ALL users
    seen_signatures = set()
    unique_bets = []
    for bet, match in all_bets:
        sig = (bet.match_id, bet.market, bet.selection)
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            unique_bets.append((bet, match))

    total_bets = len(unique_bets)
    won_bets = 0
    lost_bets = 0
    total_invested = 0.0
    total_returned = 0.0

    for bet, match in unique_bets:
        unit_stake = 1.0
        total_invested += unit_stake
        
        if bet.status == "Won":
            won_bets += 1
            total_returned += (unit_stake * bet.odds_taken)
        elif bet.status == "Lost":
            lost_bets += 1

    hit_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0.0
    net_profit = total_returned - total_invested
    hypothetical_yield = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    total_users = db.query(User).count()

    return SystemStatsResponse(
        total_predictions=total_bets,
        won_predictions=won_bets,
        lost_predictions=lost_bets,
        hit_rate=round(hit_rate, 2),
        hypothetical_yield=round(hypothetical_yield, 2),
        total_users=total_users
    )


@router.get("/predictions-detail", response_model=PredictionsDetailResponse)
def get_predictions_detail(
    days: int = Query(default=0, ge=0, description="Últimos N días (0 = Todos)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a detailed breakdown of all AI-backed bets placed in the last N days.
    (If days=0, returns all time).
    Only accessible to the admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    q = (
        db.query(Bet, Match, User)
        .join(Match, Bet.match_id == Match.id)
        .outerjoin(User, Bet.user_id == User.id)
        .filter(Bet.user_id == None)
        .filter(Bet.status.in_(["Won", "Lost", "Void"]))
    )
    
    if days > 0:
        since = datetime.utcnow() - timedelta(days=days)
        q = q.filter(Bet.placed_at >= since)

    rows = q.order_by(Bet.placed_at.desc()).all()

    # Deduplicate legacy merged bets or multiple clicks across ALL users
    seen_signatures = set()
    unique_rows = []
    for bet, match, user in rows:
        sig = (bet.match_id, bet.market, bet.selection)
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            unique_rows.append((bet, match, user))

    total = len(unique_rows)
    won = 0
    lost = 0
    pending = 0
    total_staked = 0.0
    net_pnl = 0.0
    predictions: List[PredictionDetail] = []

    for bet, match, user in unique_rows:
        if bet.status == "Won":
            won += 1
            pnl = round((bet.stake * bet.odds_taken) - bet.stake, 2)
            net_pnl += pnl
            total_staked += bet.stake
        elif bet.status == "Lost":
            lost += 1
            pnl = -round(bet.stake, 2)
            net_pnl += pnl
            total_staked += bet.stake
        elif bet.status == "Void":
            pnl = 0.0
        else:
            pending += 1
            pnl = 0.0

        home = match.home_team.name if match.home_team else "?"
        away = match.away_team.name if match.away_team else "?"

        # Reconstruct risk based on simple implied probability and odds_taken
        # Safe approximation since we only have odds_taken here
        from core.match_evaluator import _calculate_risk
        # We don't have the exact AI probability here, but odds_taken is a decent proxy.
        # However, to be more accurate, we can just pass odds_taken for both or approx prob.
        # Wait, the best way is to fetch the odds and calculate risk, but we can approximate:
        approx_prob = 1.0 / bet.odds_taken if bet.odds_taken > 0 else 0
        risk_info = _calculate_risk(approx_prob, bet.odds_taken)

        predictions.append(PredictionDetail(
            bet_id=bet.id,
            match_date=match.date.isoformat() + "Z" if match.date else "",
            home_team=home,
            away_team=away,
            market=bet.market,
            selection=bet.selection,
            odds_taken=round(bet.odds_taken, 2),
            stake=round(bet.stake, 2),
            status=bet.status,
            pnl=pnl,
            user_email=user.email if user else "unknown",
            risk_level=risk_info.get("level", "N/D"),
            risk_badge=risk_info.get("badge", "N/D"),
            risk_bg_class=risk_info.get("bgClass", "bg-gray-100 text-gray-800"),
        ))

    resolved = won + lost
    hit_rate = round((won / resolved * 100), 2) if resolved > 0 else 0.0
    yield_pct = round((net_pnl / total_staked * 100), 2) if total_staked > 0 else 0.0

    return PredictionsDetailResponse(
        period_days=days,
        total=total,
        won=won,
        lost=lost,
        pending=pending,
        hit_rate=hit_rate,
        total_staked=round(total_staked, 2),
        net_pnl=round(net_pnl, 2),
        yield_percent=yield_pct,
        predictions=predictions,
    )


@router.get("/training-report")
def get_training_report(
    current_user: User = Depends(get_current_user)
):
    """
    Returns the latest training report log as plain text.
    Only accessible to the admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "training_report.log")
    wc_meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "wc_training_meta.json")

    report_lines: list[str] = []

    # AI training log (last 500 lines)
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            report_lines += ["=== DETAILED AI LOG ==="] + lines[-500:]
        except Exception as e:
            report_lines.append(f"Error leyendo log de Clubes: {e}")

    if not report_lines:
        return PlainTextResponse(
            "No hay informes de entrenamiento aún.\nEl primer informe se generará esta madrugada a las 04:30.",
            status_code=200,
        )

    return PlainTextResponse("\n".join(str(l) for l in report_lines), status_code=200)

@router.get("/ai-info")
def get_ai_info(current_user: User = Depends(get_current_user)):
    """
    Returns metadata about the current AI models in use.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    import json
    meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "training_meta.json")
    if not os.path.exists(meta_path):
        return {"model_name": "Ensemble V2 (XGBoost + RF)", "trained_at": "No disponible", "in_use_since": "No disponible"}
        
    try:
        with open(meta_path, "r") as f:
            data = json.load(f)
            return {
                "model_name": data.get("pipeline", "Ensemble V2 (XGBoost + RF)"),
                "trained_at": data.get("completed_at", "No disponible"),
                "in_use_since": data.get("completed_at", "No disponible")
            }
    except Exception as e:
        return {"model_name": "Ensemble V2 (XGBoost + RF)", "trained_at": "Error", "in_use_since": "Error"}

@router.post("/clean-duplicates")
def trigger_duplicate_cleanup(
    current_user: User = Depends(get_current_user)
):
    """
    Triggers the one-time duplicate team/match cleanup script.
    Moved from startup background task to manual trigger to prevent
    OOM memory spikes on Render free tier.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )
    
    import sys, os
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
        
    try:
        from scripts.fix_duplicate_teams import fix_duplicate_teams
        fix_duplicate_teams()
        return {"status": "ok", "message": "Limpieza de duplicados ejecutada con éxito."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante limpieza: {str(e)}")

class TeamStatResponse(BaseModel):
    team_name: str
    matches_played: int
    goals_for: int


    goals_against: int
    wins: int
    draws: int
    losses: int
    last_updated: str
    avg_xg: Optional[float] = None
    avg_possession: Optional[float] = None
    avg_shots_on_target: Optional[float] = None

class TeamCharacteristicDTO(BaseModel):
    team_id: int
    team_name: str
    offensive_strength: float
    defensive_solidity: float
    motivation: float
    momentum: float

class UpdateTeamCharacteristicsRequest(BaseModel):
    characteristics: List[TeamCharacteristicDTO]

@router.get("/team-characteristics", response_model=List[TeamCharacteristicDTO])
def get_team_characteristics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the list of teams and their manual characteristics.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    teams = db.query(Team).order_by(Team.name).all()
    results = []
    for team in teams:
        char = team.characteristic
        if not char:
            char = TeamCharacteristic(
                team_id=team.id,
                offensive_strength=5.0,
                defensive_solidity=5.0,
                motivation=5.0,
                momentum=5.0
            )
            db.add(char)
            db.commit()
            db.refresh(char)
        
        results.append(TeamCharacteristicDTO(
            team_id=team.id,
            team_name=team.name,
            offensive_strength=char.offensive_strength,
            defensive_solidity=char.defensive_solidity,
            motivation=char.motivation,
            momentum=char.momentum
        ))
    return results

@router.put("/team-characteristics")
def update_team_characteristics(
    request: UpdateTeamCharacteristicsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the manual characteristics for multiple teams.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    for item in request.characteristics:
        char = db.query(TeamCharacteristic).filter(TeamCharacteristic.team_id == item.team_id).first()
        if char:
            char.offensive_strength = item.offensive_strength
            char.defensive_solidity = item.defensive_solidity
            char.motivation = item.motivation
            char.momentum = item.momentum
        else:
            char = TeamCharacteristic(
                team_id=item.team_id,
                offensive_strength=item.offensive_strength,
                defensive_solidity=item.defensive_solidity,
                motivation=item.motivation,
                momentum=item.momentum
            )
            db.add(char)
    db.commit()
    return {"status": "ok", "message": "Team characteristics updated."}

from fastapi import BackgroundTasks
import subprocess
import sys

@router.post("/retrain-model")
def trigger_model_retrain(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Manually triggers the AI model retraining pipeline.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    def run_retrain():
        train_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "train_model_v2.py")
        subprocess.run([sys.executable, train_script])

    background_tasks.add_task(run_retrain)
    return {"status": "ok", "message": "El reentrenamiento de La Liga ha comenzado en segundo plano."}

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
from db.models import Bet, Match, User, Team, WorldCupTeamStats, Player
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
    if current_user.email != ADMIN_EMAIL:
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
    days: int = Query(default=7, ge=1, le=90, description="Últimos N días"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a detailed breakdown of all AI-backed bets placed in the last N days
    (default: 7). Shows won/lost/pending per prediction with PnL.
    Only accessible to the admin.
    """
    if current_user.email != ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(Bet, Match, User)
        .join(Match, Bet.match_id == Match.id)
        .outerjoin(User, Bet.user_id == User.id)
        .filter(Bet.user_id == None)
        .filter(Bet.placed_at >= since)
        .filter(Bet.status.in_(["Won", "Lost", "Void"]))
        .order_by(Bet.placed_at.desc())
        .all()
    )

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
    if current_user.email != ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "training_report.log")
    wc_meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "wc_training_meta.json")

    report_lines: list[str] = []

    # World Cup AI Ensemble metadata
    if os.path.exists(wc_meta_path):
        try:
            with open(wc_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            trained_str = format_trained_at(meta.get('trained_at', 'N/A'))
            report_lines += [
                "=== WORLD CUP AI ENSEMBLE ===",
                f"Último entrenamiento : {trained_str}",
                f"Partidos históricos  : {meta.get('training_rows', 'N/A')}",
                f"Partidos Mundial '26 : {meta.get('wc_matches_used', 0)}",
                f"Jugadores evaluados  : {meta.get('players_used', 0)}",
                f"Precisión 1X2        : {meta.get('cv_1x2_acc', 0) * 100:.2f}%",
                f"LogLoss O/U 2.5      : {meta.get('cv_ou25_logloss', 0):.4f}",
                "",
            ]
        except Exception as e:
            report_lines.append(f"Error leyendo meta del Mundial: {e}\n")

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

@router.post("/clean-duplicates")
def trigger_duplicate_cleanup(
    current_user: User = Depends(get_current_user)
):
    """
    Triggers the one-time duplicate team/match cleanup script.
    Moved from startup background task to manual trigger to prevent
    OOM memory spikes on Render free tier.
    """
    if current_user.email != ADMIN_EMAIL:
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

class PlayerResponse(BaseModel):
    team_name: str
    name: str
    position: str
    rating: float
    matches_played: int
    minutes_played: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    last_updated: str

@router.get("/wc-team-stats", response_model=List[TeamStatResponse])
def get_wc_team_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    stats = db.query(WorldCupTeamStats, Team).join(Team, WorldCupTeamStats.team_id == Team.id).all()
    
    return [
        TeamStatResponse(
            team_name=t.name,
            matches_played=s.matches_played,
            goals_for=s.goals_for,
            goals_against=s.goals_against,
            wins=s.wins,
            draws=s.draws,
            losses=s.losses,
            last_updated=str(s.last_updated) if s.last_updated else ""
        ) for s, t in stats
    ]

@router.get("/wc-players", response_model=List[PlayerResponse])
def get_wc_players(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    players = db.query(Player, Team).join(Team, Player.team_id == Team.id).all()
    
    return [
        PlayerResponse(
            team_name=t.name,
            name=p.name,
            position=p.position or "",
            rating=p.rating or 0.0,
            matches_played=p.matches_played,
            minutes_played=p.minutes_played,
            goals=p.goals,
            assists=p.assists,
            yellow_cards=p.yellow_cards,
            red_cards=p.red_cards,
            last_updated=str(p.last_updated) if p.last_updated else ""
        ) for p, t in players
    ]

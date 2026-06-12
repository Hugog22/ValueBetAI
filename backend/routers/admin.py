from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from db.session import get_db
from db.models import Bet, Match, Prediction, User
from routers.auth import get_current_user

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
    if current_user.email != "hugodesax123@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    all_bets = (
        db.query(Bet, Match)
        .join(Match, Bet.match_id == Match.id)
        .filter(Bet.status.in_(["Won", "Lost"]))
        .all()
    )

    total_bets = len(all_bets)
    won_bets = 0
    lost_bets = 0
    total_invested = 0.0
    total_returned = 0.0

    for bet, match in all_bets:
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
    if current_user.email != "hugodesax123@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta página."
        )

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(Bet, Match, User)
        .join(Match, Bet.match_id == Match.id)
        .join(User, Bet.user_id == User.id)
        .filter(Bet.placed_at >= since)
        .order_by(Bet.placed_at.desc())
        .all()
    )

    total = len(rows)
    won = 0
    lost = 0
    pending = 0
    total_staked = 0.0
    net_pnl = 0.0
    predictions: List[PredictionDetail] = []

    for bet, match, user in rows:
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

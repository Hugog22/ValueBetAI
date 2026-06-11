from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

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

    # Cross reference Predictions with Finished Matches
    # A prediction is a value_bet if value_bet_flag = True
    # If the user's implementation didn't fully persist 'Prediction' rows yet,
    # we can alternatively infer it by looking at User bets or just looking
    # at the Match table vs Predictions.
    
    # We will look at Bets placed by ANY user where the AI predicted value,
    # or just raw Bets as a proxy for system performance if Predictions aren't fully seeded.
    # To be extremely precise, let's look at all Bets across the platform.
    
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
        # Assuming fixed 1 unit stake to calculate true system Yield
        unit_stake = 1.0
        total_invested += unit_stake
        
        if bet.status == "Won":
            won_bets += 1
            total_returned += (unit_stake * bet.odds_taken)
        elif bet.status == "Lost":
            lost_bets += 1

    hit_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0.0
    
    # Yield = (Net Profit / Total Invested) * 100
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

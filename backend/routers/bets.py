from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List

from db.session import get_db
from db.models import Bet, Match
from routers.auth import get_current_user, User
from core.match_evaluator import _evaluate_match as _evaluate_match_core
from core.shared_predictor import predictor

def _evaluate_match(match: Match, db: Session | None = None) -> dict:
    return _evaluate_match_core(match, predictor, db)

router = APIRouter(prefix="/api", tags=["bets"])

class BetCreate(BaseModel):
    match_id: int
    bookmaker: str
    market: str
    selection: str
    odds_taken: float
    stake: float

class BetResponse(BaseModel):
    id: int
    match_id: int
    home_team: str
    away_team: str
    bookmaker: str
    market: str
    selection: str
    odds_taken: float
    stake: float
    pnl: float | None
    status: str
    clv: float | None
    created_at: str
    risk_level: str | None
    risk_badge: str | None
    risk_bg_class: str | None

    class Config:
        from_attributes = True

class BankrollStats(BaseModel):
    total_staked: float
    total_pnl: float
    roi: float
    yield_percent: float
    win_rate: float
    total_bets: int
    won_bets: int
    lost_bets: int
    recent_bets: List[BetResponse]

@router.post("/bets")
def place_virtual_bet(
    bet_in: BetCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Simulate a bet on a given match."""
    match = db.query(Match).filter(Match.id == bet_in.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    new_bet = Bet(
        user_id=current_user.id,
        match_id=bet_in.match_id,
        bookmaker=bet_in.bookmaker,
        market=bet_in.market,
        selection=bet_in.selection,
        odds_taken=bet_in.odds_taken,
        stake=bet_in.stake,
        status="Pending",
        clv=None  # Can be updated later when match starts
    )
    db.add(new_bet)
    db.commit()
    db.refresh(new_bet)
    return {"status": "success", "bet_id": new_bet.id}

@router.get("/bankroll/stats", response_model=BankrollStats)
def get_bankroll_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate and return holistic virtual bankroll metrics."""
    # Re-evaluate all returned bets to map teams for the frontend
    all_bets_query = (
        db.query(Bet, Match)
        .join(Match, Bet.match_id == Match.id)
        .filter(Bet.user_id == current_user.id)
    )
    all_bets_data = all_bets_query.all()
    
    total_staked = 0.0
    net_profit = 0.0
    won_bets = 0
    lost_bets = 0

    recent_bets = []
    
    for bet, match in all_bets_data:
        # Calculate PnL for resolved bets
        if bet.status == "Won":
            profit = (bet.stake * bet.odds_taken) - bet.stake
            net_profit += profit
            total_staked += bet.stake
            won_bets += 1
        elif bet.status == "Lost":
            net_profit -= bet.stake
            total_staked += bet.stake
            lost_bets += 1
        elif bet.status == "Void":
            pass # Refunded, no action needed on profit
            
        # Collect recent bets mapping team names
        res = BetResponse(
            id=bet.id,
            match_id=bet.match_id,
            home_team=match.home_team.name,
            away_team=match.away_team.name,
            bookmaker=bet.bookmaker,
            market=bet.market,
            selection=bet.selection,
            odds_taken=bet.odds_taken,
            stake=bet.stake,
            status=bet.status,
            pnl=round(((bet.stake * bet.odds_taken) - bet.stake) if bet.status == "Won" else (-bet.stake if bet.status == "Lost" else 0.0), 2),
            clv=bet.clv,
            created_at=bet.placed_at.isoformat() + "Z" if bet.placed_at else "",
            risk_level="MEDIO",
            risk_badge="🟡 MEDIO",
            risk_bg_class="bg-yellow-400 text-black font-bold"
        )
        
        # Try to find risk if it's a recent match we can re-evaluate
        try:
            eval_data = _evaluate_match(match, db)
            risk = eval_data["bestPick"]["risk"]
            res.risk_level = risk["level"]
            res.risk_badge = risk["badge"]
            res.risk_bg_class = risk["bgClass"]
        except Exception:
            pass

        recent_bets.append(res)
    
    # Ensure they are sorted by recency
    recent_bets.sort(key=lambda x: x.id, reverse=True)
    
    total_resolved = won_bets + lost_bets
    hit_rate = (won_bets / total_resolved * 100) if total_resolved > 0 else 0.0
    yield_percent = (net_profit / total_staked * 100) if total_staked > 0 else 0.0
    
    # ROI can refer to return on starting bankroll, but without a defined starting bank, Yield is usually what users mean by ROI. 
    # Yield is Net Profit / Total Staked * 100
    # Let's align ROI to Yield here as is common in betting (unless a specific initial Bankroll is given)
    roi_percent = yield_percent
    
    return BankrollStats(
        total_staked=round(total_staked, 2),
        total_pnl=round(net_profit, 2),
        roi=round(roi_percent, 2),
        yield_percent=round(yield_percent, 2),
        win_rate=round(hit_rate, 2),
        total_bets=len(all_bets_data),
        won_bets=won_bets,
        lost_bets=lost_bets,
        recent_bets=recent_bets[:20]  # Return last 20 for UI
    )

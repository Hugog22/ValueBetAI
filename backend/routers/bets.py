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
    match_date: str
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
    current_bankroll: float
    recent_bets: List[BetResponse]

@router.post("/bets")
def place_virtual_bet(
    bet_in: BetCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Simulate a bet on a given match."""
    try:
        match = db.query(Match).filter(Match.id == bet_in.match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        # Safe bankroll access (handles missing column in older DB schemas)
        try:
            current_bankroll = float(current_user.bankroll or 0) or 1000.0
        except Exception:
            current_bankroll = 1000.0

        if bet_in.stake <= 0:
            raise HTTPException(status_code=400, detail="El stake debe ser mayor que 0")
        if bet_in.stake > current_bankroll:
            raise HTTPException(status_code=400, detail=f"Saldo insuficiente. Disponible: {current_bankroll:.2f} \u20ac")

        # Deduct stake immediately from bankroll
        try:
            current_user.bankroll = current_bankroll - bet_in.stake
        except Exception:
            pass  # If column missing, skip — still record the bet

        new_bet = Bet(
            user_id=current_user.id,
            match_id=bet_in.match_id,
            bookmaker=bet_in.bookmaker,
            market=bet_in.market,
            selection=bet_in.selection,
            odds_taken=bet_in.odds_taken,
            stake=bet_in.stake,
            status="Pending",
            clv=None
        )
        db.add(new_bet)
        db.commit()
        db.refresh(new_bet)

        new_bankroll = current_bankroll - bet_in.stake
        return {
            "status": "success",
            "bet_id": new_bet.id,
            "new_bankroll": round(new_bankroll, 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar apuesta: {str(e)}")


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
            match_date=match.date.isoformat() + "Z" if match.date else "",
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
        current_bankroll=current_user.bankroll or 1000.0,
        recent_bets=recent_bets[:20]  # Return last 20 for UI
    )


@router.post("/bets/settle")
def manually_settle_bets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger bet settlement for all pending bets on finished matches.
    Useful for testing and forcing an immediate settlement without waiting
    for the hourly scheduler job.
    """
    from core.bet_settler import settle_pending_bets
    try:
        summary = settle_pending_bets()
        return {
            "status": "ok",
            "settled": summary["settled"],
            "won": summary["won"],
            "lost": summary["lost"],
            "void": summary["void"],
            "bankroll_credited": summary["bankroll_credited"],
            "errors": summary["errors"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Settlement failed: {str(e)}")


@router.get("/bets/settle/status")
def get_settle_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Return how many of the current user's bets are still pending settlement,
    and how many already have a result.
    """
    from db.models import Match
    pending_count = (
        db.query(Bet)
        .join(Match, Bet.match_id == Match.id)
        .filter(
            Bet.user_id == current_user.id,
            Bet.status == "Pending",
            Match.status == "Finished",
        )
        .count()
    )
    total_pending = (
        db.query(Bet)
        .filter(Bet.user_id == current_user.id, Bet.status == "Pending")
        .count()
    )
    return {
        "total_pending_bets": total_pending,
        "pending_on_finished_matches": pending_count,
        "message": (
            f"{pending_count} apuesta(s) listas para liquidar."
            if pending_count > 0
            else "No hay apuestas pendientes de liquidar."
        )
    }


"""
bet_settler.py
--------------
Automated settlement of pending bets based on match results.

This module is called by the scheduler (hourly) and by the ETL pipeline
after each data sync. It resolves Pending bets for Finished matches and
adjusts the user's bankroll accordingly.

Settlement logic:
  1x2 market  — "Home" wins if home_goals > away_goals
                "Away" wins if away_goals > home_goals
                "Draw" wins if home_goals == away_goals
  ou25 market — "Over 2.5" wins if total_goals > 2
                "Under 2.5" wins if total_goals <= 2

Bankroll:
  - Stake was already deducted when the bet was placed.
  - On Win: add back stake + profit  (= stake * odds_taken)
  - On Loss: nothing to do (stake already deducted)
"""

import logging
from datetime import datetime
from typing import Tuple

logger = logging.getLogger(__name__)


def _determine_outcome(selection: str, market: str, home_goals: int, away_goals: int) -> str:
    """
    Determine 'Won', 'Lost', or 'Void' for a given bet selection.

    Args:
        selection:   e.g. "Home", "Away", "Draw", "Over 2.5", "Under 2.5"
        market:      e.g. "1x2", "ou25"  (used as hint but selection is primary)
        home_goals:  home team goals scored
        away_goals:  away team goals scored

    Returns:
        'Won', 'Lost', or 'Void'
    """
    total_goals = home_goals + away_goals
    sel = selection.strip().lower()

    # 1x2
    if sel in ("home", "victoria local"):
        return "Won" if home_goals > away_goals else "Lost"
    if sel in ("away", "victoria visitante"):
        return "Won" if away_goals > home_goals else "Lost"
    if sel in ("draw", "empate", "x"):
        return "Won" if home_goals == away_goals else "Lost"

    # Over/Under 2.5
    if "over" in sel or "más de 2.5" in sel or "mas de 2.5" in sel:
        return "Won" if total_goals > 2 else "Lost"
    if "under" in sel or "menos de 2.5" in sel:
        return "Won" if total_goals <= 2 else "Lost"

    # Unknown selection — mark Void to avoid unfair deductions
    logger.warning(f"⚠️  Unknown selection '{selection}' for market '{market}'. Marking Void.")
    return "Void"


def settle_pending_bets() -> dict:
    """
    Settle all Pending bets whose match is now Finished.

    Returns a summary dict:
        {
            "settled":  int,   # total bets resolved
            "won":      int,
            "lost":     int,
            "void":     int,
            "bankroll_credited": float,  # total € returned to users (wins)
            "errors":   int,
        }
    """
    from db.session import SessionLocal
    from db.models import Bet, Match, User

    db = SessionLocal()
    summary = {"settled": 0, "won": 0, "lost": 0, "void": 0, "bankroll_credited": 0.0, "errors": 0}

    try:
        # Join Bet → Match; only look at bets that are still Pending
        # and whose match is Finished (has result data)
        pending_bets = (
            db.query(Bet, Match)
            .join(Match, Bet.match_id == Match.id)
            .filter(
                Bet.status == "Pending",
                Match.status == "Finished",
                Match.home_goals != None,  # noqa: E711
                Match.away_goals != None,  # noqa: E711
            )
            .all()
        )

        if not pending_bets:
            logger.info("✅ [bet_settler] No pending bets to settle.")
            return summary

        logger.info(f"🎲 [bet_settler] Found {len(pending_bets)} pending bets to settle.")

        for bet, match in pending_bets:
            try:
                outcome = _determine_outcome(
                    selection=bet.selection,
                    market=bet.market,
                    home_goals=match.home_goals,
                    away_goals=match.away_goals,
                )

                bet.status = outcome
                summary["settled"] += 1

                if outcome == "Won":
                    summary["won"] += 1
                    # Return stake + profit to user's bankroll
                    payout = round(float(bet.stake) * float(bet.odds_taken), 2)
                    summary["bankroll_credited"] += payout
                    try:
                        user = db.query(User).filter(User.id == bet.user_id).first()
                        if user:
                            current = float(user.bankroll or 0)
                            user.bankroll = round(current + payout, 2)
                    except Exception as e:
                        logger.warning(f"⚠️  Could not update bankroll for user {bet.user_id}: {e}")

                elif outcome == "Void":
                    summary["void"] += 1
                    # Refund the stake
                    try:
                        user = db.query(User).filter(User.id == bet.user_id).first()
                        if user:
                            current = float(user.bankroll or 0)
                            user.bankroll = round(current + float(bet.stake), 2)
                            summary["bankroll_credited"] += float(bet.stake)
                    except Exception as e:
                        logger.warning(f"⚠️  Could not refund void bet for user {bet.user_id}: {e}")
                else:
                    summary["lost"] += 1

                logger.info(
                    f"  → Bet #{bet.id} | {match.home_team_id}v{match.away_team_id} "
                    f"| '{bet.selection}' → {outcome} "
                    f"(goals: {match.home_goals}-{match.away_goals})"
                )

            except Exception as e:
                logger.error(f"❌ [bet_settler] Error settling bet #{bet.id}: {e}", exc_info=True)
                summary["errors"] += 1
                continue

        db.commit()
        logger.info(
            f"✅ [bet_settler] Settlement complete: "
            f"{summary['won']} Won / {summary['lost']} Lost / {summary['void']} Void "
            f"| Bankroll credited: €{summary['bankroll_credited']:.2f}"
        )

    except Exception as e:
        logger.error(f"❌ [bet_settler] Fatal error during settlement: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

    return summary

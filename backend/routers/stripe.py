import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime

from db.session import get_db
from db.models import User
from routers.auth import get_current_user
from core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY.strip() if settings.STRIPE_SECRET_KEY else ""
webhook_secret = settings.STRIPE_WEBHOOK_SECRET.strip() if settings.STRIPE_WEBHOOK_SECRET else ""
price_id = settings.STRIPE_PRICE_ID.strip() if settings.STRIPE_PRICE_ID else ""
frontend_url = settings.FRONTEND_URL.strip() if settings.FRONTEND_URL else "https://value-bet-ai.vercel.app"

router = APIRouter(prefix="/api/stripe", tags=["Stripe"])

TRIAL_PERIOD_DAYS = 7

@router.post("/create-checkout-session")
def create_checkout_session(current_user: User = Depends(get_current_user)):
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe Price ID not configured.")
        
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            subscription_data={
                # No trial period
            },
            success_url=f"{frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/register",
            client_reference_id=str(current_user.id),
            customer_email=current_user.email,
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-portal-session")
def create_portal_session(current_user: User = Depends(get_current_user)):
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No stripe customer found")
    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{frontend_url}/bankroll"
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify-session")
def verify_session(session_id: str, current_user: User = Depends(get_current_user)):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid' or session.status == 'complete':
            return {"status": "paid", "subscription_status": "active"}
        elif session.status == 'complete':
            # Trial period — no payment yet but subscription is active in trial
            return {"status": "trialing", "subscription_status": "trialing"}
        else:
            return {"status": "unpaid", "subscription_status": "inactive"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        if not webhook_secret:
            raise HTTPException(status_code=503, detail="Stripe webhook secret not configured")
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.client_reference_id
        customer_id = session.customer
        
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.stripe_customer_id = customer_id
                # For trials, subscription starts as 'trialing'; for direct subs, 'active'
                subscription_status = getattr(session, 'subscription', None)
                user.subscription_status = 'trialing' if session.get('subscription') else 'active'
                db.commit()

    elif event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        customer_id = subscription.customer
        sub_status = subscription.status  # 'trialing', 'active', etc.
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = sub_status
            period_end = getattr(subscription, 'current_period_end', None)
            if period_end:
                user.subscription_end_date = datetime.utcfromtimestamp(period_end)
            db.commit()

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.customer
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = 'canceled'
            db.commit()

    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        customer_id = subscription.customer
        sub_status = subscription.status
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = sub_status
            
            # Save the end date of the current billing period (or cancellation date)
            period_end = getattr(subscription, 'current_period_end', None)
            if period_end:
                user.subscription_end_date = datetime.utcfromtimestamp(period_end)
                
            db.commit()

    return {"status": "success"}

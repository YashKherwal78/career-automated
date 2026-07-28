"""
Billing — Razorpay Checkout integration.

POST /billing/create-order   Creates a Razorpay order for the Pro plan, records it as 'created'.
POST /billing/verify-payment Verifies the Razorpay signature, marks the order 'paid'.
GET  /billing/subscription   Returns the caller's current plan ('free' or 'pro').
"""

from __future__ import annotations

import hashlib
import hmac

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.runtime.auth.dependencies import get_current_user, CurrentUser
from src.runtime.config.settings import Settings
from src.runtime.postgres.connection import get_connection

router = APIRouter()

# CareerAutomated Pro: ₹500 + 18% GST, in paise.
PRO_PLAN_AMOUNT_PAISE = 59000
PRO_PLAN_CURRENCY = "INR"

RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"


class VerifyPaymentPayload(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/create-order")
def create_order(current_user: CurrentUser = Depends(get_current_user)):
    if not Settings.RAZORPAY_KEY_ID or not Settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Razorpay is not configured on this server.",
        )

    resp = requests.post(
        RAZORPAY_ORDERS_URL,
        auth=(Settings.RAZORPAY_KEY_ID, Settings.RAZORPAY_KEY_SECRET),
        json={
            "amount": PRO_PLAN_AMOUNT_PAISE,
            "currency": PRO_PLAN_CURRENCY,
            "receipt": f"pro_{current_user.user_id}",
            "payment_capture": 1,
        },
        timeout=15,
    )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Razorpay order creation failed: {resp.text}",
        )
    order = resp.json()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO public.user_subscriptions
                (user_id, plan, razorpay_order_id, amount, currency, status)
            VALUES (%s, 'pro', %s, %s, %s, 'created')
            """,
            (current_user.user_id, order["id"], PRO_PLAN_AMOUNT_PAISE, PRO_PLAN_CURRENCY),
        )
        conn.commit()

    return {
        "order_id": order["id"],
        "amount": PRO_PLAN_AMOUNT_PAISE,
        "currency": PRO_PLAN_CURRENCY,
        "key_id": Settings.RAZORPAY_KEY_ID,
    }


@router.post("/verify-payment")
def verify_payment(
    payload: VerifyPaymentPayload,
    current_user: CurrentUser = Depends(get_current_user),
):
    expected_signature = hmac.new(
        key=Settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        msg=f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, payload.razorpay_signature):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE public.user_subscriptions SET status = 'failed'
                WHERE razorpay_order_id = %s AND user_id = %s
                """,
                (payload.razorpay_order_id, current_user.user_id),
            )
            conn.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment signature verification failed.",
        )

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE public.user_subscriptions
            SET razorpay_payment_id = %s, razorpay_signature = %s, status = 'paid', paid_at = NOW()
            WHERE razorpay_order_id = %s AND user_id = %s
            """,
            (
                payload.razorpay_payment_id,
                payload.razorpay_signature,
                payload.razorpay_order_id,
                current_user.user_id,
            ),
        )
        conn.commit()

    return {"status": "paid"}


@router.get("/subscription")
def get_subscription(current_user: CurrentUser = Depends(get_current_user)):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT plan, status, paid_at FROM public.user_subscriptions
            WHERE user_id = %s AND status = 'paid'
            ORDER BY paid_at DESC LIMIT 1
            """,
            (current_user.user_id,),
        )
        row = cursor.fetchone()
        if row:
            return {"tier": row[0], "active_since": row[2].isoformat() if row[2] else None}
        return {"tier": "free", "active_since": None}

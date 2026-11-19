"""Consultation-fee payments (Sprint 7).

PAYMENT_PROVIDER in .env:
    mock       demo gateway for development and tests - no money moves (default)
    razorpay   real Razorpay Checkout; needs RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET

Flow: create_order() -> browser pays -> verify_payment() checks the gateway signature.
"""
import base64
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone

from .models import Payment


class PaymentError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def provider():
    return getattr(settings, "PAYMENT_PROVIDER", "mock")

def commission_percent():
    """The platform's cut of each fee, from PLATFORM_COMMISSION_PERCENT in .env (default 10)."""
    try:
        pct = Decimal(str(getattr(settings, "PLATFORM_COMMISSION_PERCENT", "10")))
    except InvalidOperation:
        pct = Decimal("10")
    return min(max(pct, Decimal("0")), Decimal("100"))


def apply_split(payment):
    """Fix the platform / hospital shares of a payment that has just succeeded."""
    amount = Decimal(payment.amount)
    commission = (amount * commission_percent() / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    payment.commission_amount = commission
    payment.hospital_amount = amount - commission
def fee_for(appointment):
    return Decimal(appointment.doctor.consultation_fee or 0)


def payment_state(appointment):
    """NOT_REQUIRED / UNPAID / PAID / REFUND_DUE - what the screens show."""
    payment = getattr(appointment, "payment", None)   # None when no payment row exists yet
    if payment is not None and payment.status in (Payment.STATUS_PAID, Payment.STATUS_REFUND_DUE):
        return payment.status
    if fee_for(appointment) <= 0:
        return "NOT_REQUIRED"
    return "UNPAID"


def _razorpay_order(amount_paise, receipt):
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    if not (key_id and key_secret):
        raise PaymentError("Razorpay is not configured on the server.", 503)
    body = json.dumps({"amount": amount_paise, "currency": "INR", "receipt": receipt, "payment_capture": 1}).encode()
    request = urllib.request.Request("https://api.razorpay.com/v1/orders", data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", "Basic " + base64.b64encode(f"{key_id}:{key_secret}".encode()).decode())
    try:
        return json.loads(urllib.request.urlopen(request, timeout=15).read().decode())
    except (urllib.error.URLError, ValueError) as exc:
        raise PaymentError("The payment gateway is not reachable right now. Please try again.", 502) from exc


def create_order(appointment):
    amount = fee_for(appointment)
    if amount <= 0:
        raise PaymentError("This doctor has no consultation fee to pay.")
    payment, _ = Payment.objects.get_or_create(
        appointment=appointment, defaults={"amount": amount, "currency": "INR"}
    )
    if payment.status in (Payment.STATUS_PAID, Payment.STATUS_REFUND_DUE):
        raise PaymentError("This appointment is already paid.", 409)

    active = provider()
    if active == "razorpay":
        order = _razorpay_order(int((amount * 100).to_integral_value()), f"appt-{appointment.id}")
        order_id = order.get("id", "")
        if not order_id:
            raise PaymentError("The payment gateway did not return an order.", 502)
    else:
        order_id = f"mock_order_{appointment.id}_{secrets.token_hex(4)}"

    payment.amount = amount
    payment.provider = active
    payment.provider_order_id = order_id
    payment.status = Payment.STATUS_PENDING
    payment.save()
    return {
        "payment_id": payment.id,
        "provider": active,
        "order_id": order_id,
        "amount": str(amount),
        "amount_paise": int((amount * 100).to_integral_value()),
        "currency": payment.currency,
        "key_id": getattr(settings, "RAZORPAY_KEY_ID", "") if active == "razorpay" else "",
    }


def verify_payment(appointment, order_id, gateway_payment_id, signature):
    payment = getattr(appointment, "payment", None)
    if payment is None:
        raise PaymentError("No payment was started for this appointment.", 404)
    if payment.status == Payment.STATUS_PAID:
        return payment  # a repeated confirmation is harmless
    if not order_id or order_id != payment.provider_order_id:
        raise PaymentError("This payment does not belong to the current order.")

    if payment.provider == Payment.PROVIDER_RAZORPAY:
        secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
        expected = hmac.new(secret.encode(), f"{order_id}|{gateway_payment_id}".encode(), hashlib.sha256).hexdigest()
        if not (secret and gateway_payment_id and hmac.compare_digest(expected, signature or "")):
            raise PaymentError("Payment verification failed.")
    elif payment.provider == Payment.PROVIDER_MOCK and provider() == "mock":
        if signature != "mock-signature":
            raise PaymentError("Payment verification failed.")
        gateway_payment_id = gateway_payment_id or f"mock_pay_{secrets.token_hex(4)}"
    else:
        raise PaymentError("This payment cannot be confirmed with the current gateway settings.")

    payment.status = Payment.STATUS_PAID
    payment.provider_payment_id = gateway_payment_id
    payment.paid_at = timezone.now()
    payment.save()
    return payment


def record_cash(appointment):
    amount = fee_for(appointment)
    if amount <= 0:
        raise PaymentError("This doctor has no consultation fee.")
    payment, _ = Payment.objects.get_or_create(
        appointment=appointment, defaults={"amount": amount, "currency": "INR"}
    )
    if payment.status in (Payment.STATUS_PAID, Payment.STATUS_REFUND_DUE):
        raise PaymentError("This appointment is already paid.", 409)
    payment.amount = amount
    payment.provider = Payment.PROVIDER_CASH
    payment.provider_payment_id = "cash"
    payment.status = Payment.STATUS_PAID
    payment.paid_at = timezone.now()
    payment.save()
    return payment


def mark_refund_due(appointment):
    """Called when a paid appointment is cancelled. Returns True if a refund is now due."""
    payment = getattr(appointment, "payment", None)
    if payment is not None and payment.status == Payment.STATUS_PAID:
        payment.status = Payment.STATUS_REFUND_DUE
        payment.save(update_fields=["status", "updated_at"])
        return True
    return False

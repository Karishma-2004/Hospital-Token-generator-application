"""Marketplace settlements: patients pay the platform, the platform keeps its commission,
the admin pays the rest out to each hospital and records every transfer.

Per hospital:
    online_paid  fees paid online (these reached the platform's gateway account)
    cash_paid    fees the hospital took in cash at its own desk (the hospital already has this money)
    commission   the platform's cut of ALL paid fees (online and cash)
    net_due      online_paid - commission     what the platform owes the hospital
    paid_out     transfers already made
    balance      net_due - paid_out           negative = the hospital owes the platform
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Payment, Payout
from appointments.payments import commission_percent
from doctors.access import IsApplicationAdmin
from doctors.models import Hospital

ZERO = Decimal("0.00")
PAID = Q(appointments__payment__status=Payment.STATUS_PAID)
CASH = Q(appointments__payment__provider=Payment.PROVIDER_CASH)
ONLINE = Q(appointments__payment__provider__in=[Payment.PROVIDER_RAZORPAY, Payment.PROVIDER_MOCK])


def _d(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def settlement_rows(hospital_id=None):
    hospitals = Hospital.objects.all()
    if hospital_id:
        hospitals = hospitals.filter(id=hospital_id)
    hospitals = hospitals.annotate(
        online_paid=Sum("appointments__payment__amount", filter=PAID & ONLINE),
        cash_paid=Sum("appointments__payment__amount", filter=PAID & CASH),
        commission=Sum("appointments__payment__commission_amount", filter=PAID),
        refund_due=Sum(
            "appointments__payment__amount",
            filter=Q(appointments__payment__status=Payment.STATUS_REFUND_DUE) & ONLINE,
        ),
    ).order_by("name")
    payouts = {
        r["hospital_id"]: r["total"]
        for r in Payout.objects.values("hospital_id").annotate(total=Sum("amount"))
    }
    rows = []
    for h in hospitals:
        online, cash, commission = _d(h.online_paid), _d(h.cash_paid), _d(h.commission)
        net_due = online - commission
        paid_out = _d(payouts.get(h.id))
        rows.append({
            "hospital_id": h.id, "hospital": h.name, "city": h.city, "status": h.status,
            "online_paid": online, "cash_paid": cash, "commission": commission,
            "net_due": net_due, "paid_out": paid_out, "balance": net_due - paid_out,
            "refund_due": _d(h.refund_due),
        })
    return rows


def _text(row):
    return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in row.items()}


class SettlementListView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get(self, request):
        rows = settlement_rows()
        totals = {
            key: str(sum((r[key] for r in rows), ZERO))
            for key in ("online_paid", "cash_paid", "commission", "net_due", "paid_out", "balance", "refund_due")
        }
        return Response({
            "commission_percent": str(commission_percent()),
            "rows": [_text(r) for r in rows],
            "totals": totals,
        })


class PayoutView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get(self, request):
        qs = Payout.objects.select_related("hospital", "paid_by")
        hospital_id = request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        return Response([
            {
                "id": p.id, "hospital_id": p.hospital_id, "hospital": p.hospital.name, "amount": str(p.amount),
                "reference": p.reference, "note": p.note,
                "paid_by": (p.paid_by.get_full_name() or p.paid_by.username) if p.paid_by else "",
                "created_at": p.created_at.isoformat(),
            }
            for p in qs[:200]
        ])

    def post(self, request):
        hospital = Hospital.objects.filter(id=request.data.get("hospital")).first()
        if not hospital:
            return Response({"hospital": ["Select a hospital."]}, status=400)
        try:
            amount = Decimal(str(request.data.get("amount", ""))).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return Response({"amount": ["Enter a valid amount."]}, status=400)
        reference = str(request.data.get("reference", "")).strip()
        if amount <= 0:
            return Response({"amount": ["Amount must be more than zero."]}, status=400)
        if not reference:
            return Response({"reference": ["Enter the bank / UPI reference number of the transfer."]}, status=400)

        with transaction.atomic():
            balance = settlement_rows(hospital.id)[0]["balance"]
            if balance <= 0:
                return Response({"amount": ["Nothing is owed to this hospital right now."]}, status=400)
            if amount > balance:
                return Response(
                    {"amount": [f"The hospital is owed only INR {balance}. You cannot pay out more than that."]},
                    status=400,
                )
            payout = Payout.objects.create(
                hospital=hospital, amount=amount, reference=reference[:100],
                note=str(request.data.get("note", ""))[:200], paid_by=request.user,
            )
        return Response({"id": payout.id, "amount": str(payout.amount), "balance": str(balance - amount)}, status=201)
"""Sprint 8 - Application Admin dashboard, reports and user management.

Every endpoint needs a valid JWT of an Application Admin (see doctors.access.IsApplicationAdmin).
"""
import csv
from datetime import date, timedelta

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, ProtectedError, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from appointments.models import Appointment, Payment
from doctors.access import IsApplicationAdmin
from doctors.models import DoctorProfile, Hospital, HospitalStaff


def _int(value, default, low, high):
    try:
        return max(low, min(int(value), high))
    except (TypeError, ValueError):
        return default


def _date(value, default):
    try:
        return date.fromisoformat(value) if value else default
    except ValueError:
        return default


# ======================================================================
# Dashboard numbers
# ======================================================================
class StatsView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get(self, request):
        days = _int(request.query_params.get("days"), 30, 7, 365)
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)

        users_by_role = {r["role"]: r["n"] for r in User.objects.values("role").annotate(n=Count("id"))}
        hospitals_by_status = {r["status"]: r["n"] for r in Hospital.objects.values("status").annotate(n=Count("id"))}
        appointments_by_status = {
            r["status"]: r["n"] for r in Appointment.objects.values("status").annotate(n=Count("id"))
        }

        rows = (
            Appointment.objects.filter(appointment_date__range=(start, today))
            .values("appointment_date")
            .annotate(
                total=Count("id"),
                completed=Count("id", filter=Q(status=Appointment.STATUS_COMPLETED)),
                cancelled=Count("id", filter=Q(status=Appointment.STATUS_CANCELLED)),
            )
        )
        by_day = {r["appointment_date"]: r for r in rows}
        daily = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            r = by_day.get(day)
            daily.append({
                "date": day.isoformat(),
                "total": r["total"] if r else 0,
                "completed": r["completed"] if r else 0,
                "cancelled": r["cancelled"] if r else 0,
            })

        paid = Payment.objects.filter(status=Payment.STATUS_PAID)
        revenue_total = paid.aggregate(t=Sum("amount"))["t"] or 0
        revenue_range = paid.filter(paid_at__date__range=(start, today)).aggregate(t=Sum("amount"))["t"] or 0
        commission_total = paid.aggregate(t=Sum("commission_amount"))["t"] or 0
        commission_range = (
            paid.filter(paid_at__date__range=(start, today)).aggregate(t=Sum("commission_amount"))["t"] or 0
        )

        top_hospitals = Hospital.objects.annotate(n=Count("appointments")).filter(n__gt=0).order_by("-n", "name")[:5]
        top_doctors = (
            DoctorProfile.objects.select_related("user", "hospital")
            .annotate(n=Count("appointments", filter=Q(appointments__status=Appointment.STATUS_COMPLETED)))
            .filter(n__gt=0).order_by("-n")[:5]
        )

        return Response({
            "days": days,
            "users": {
                "total": sum(users_by_role.values()),
                "active": User.objects.filter(is_active=True).count(),
                "by_role": users_by_role,
            },
            "hospitals": {"total": sum(hospitals_by_status.values()), "by_status": hospitals_by_status},
            "appointments": {
                "total": sum(appointments_by_status.values()),
                "today": Appointment.objects.filter(appointment_date=today)
                .exclude(status=Appointment.STATUS_CANCELLED).count(),
                "walk_ins": Appointment.objects.filter(is_walk_in=True).count(),
                "by_status": appointments_by_status,
            },
            "revenue": {
                "total": str(revenue_total), "in_period": str(revenue_range), "currency": "INR",
                "commission_total": str(commission_total), "commission_in_period": str(commission_range),
            },            "daily": daily,
            "top_hospitals": [{"id": h.id, "name": h.name, "appointments": h.n} for h in top_hospitals],
            "top_doctors": [
                {
                    "id": d.id,
                    "name": f"Dr. {d.user.first_name} {d.user.last_name}".strip(),
                    "hospital": d.hospital.name,
                    "completed": d.n,
                }
                for d in top_doctors
            ],
        })


# ======================================================================
# Report per hospital (+ CSV)
# ======================================================================
def _safe_cell(value):
    """Stop spreadsheet programs from running a cell that starts with = + - @ as a formula."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


class ReportView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get(self, request):
        today = timezone.localdate()
        end = _date(request.query_params.get("to"), today)
        start = _date(request.query_params.get("from"), end - timedelta(days=29))
        if start > end:
            return Response({"detail": "The 'from' date must not be after the 'to' date."}, status=400)

        in_range = Q(appointments__appointment_date__range=(start, end))
        hospitals = Hospital.objects.annotate(
            total=Count("appointments", filter=in_range),
            completed=Count("appointments", filter=in_range & Q(appointments__status=Appointment.STATUS_COMPLETED)),
            cancelled=Count("appointments", filter=in_range & Q(appointments__status=Appointment.STATUS_CANCELLED)),
            no_show=Count(
                "appointments",
                filter=in_range & Q(appointments__status=Appointment.STATUS_BOOKED, appointments__appointment_date__lt=today),
            ),
            walk_ins=Count("appointments", filter=in_range & Q(appointments__is_walk_in=True)),
            revenue=Sum(
                "appointments__payment__amount",
                filter=in_range & Q(appointments__payment__status=Payment.STATUS_PAID),
            ),
        ).order_by("name")

        rows = [
            {
                "hospital": h.name, "city": h.city, "status": h.status,
                "appointments": h.total, "completed": h.completed, "cancelled": h.cancelled,
                "no_show": h.no_show, "walk_ins": h.walk_ins, "revenue": str(h.revenue or 0),
            }
            for h in hospitals
        ]
        totals = {
            key: sum(r[key] for r in rows)
            for key in ("appointments", "completed", "cancelled", "no_show", "walk_ins")
        }
        totals["revenue"] = str(sum((h.revenue or 0) for h in hospitals))

        if request.query_params.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="medibook-report-{start}-to-{end}.csv"'
            writer = csv.writer(response)
            writer.writerow(["Hospital", "City", "Status", "Appointments", "Completed", "Cancelled",
                             "No-show", "Walk-ins", "Revenue (INR)"])
            for r in rows:
                writer.writerow([_safe_cell(r["hospital"]), _safe_cell(r["city"]), r["status"], r["appointments"],
                                 r["completed"], r["cancelled"], r["no_show"], r["walk_ins"], r["revenue"]])
            writer.writerow(["TOTAL", "", "", totals["appointments"], totals["completed"], totals["cancelled"],
                             totals["no_show"], totals["walk_ins"], totals["revenue"]])
            return response

        return Response({"from": start.isoformat(), "to": end.isoformat(), "rows": rows, "totals": totals})


# ======================================================================
# Users: list, deactivate / reactivate, delete
# ======================================================================
def _user_row(u):
    hospital = None
    staff = getattr(u, "hospital_staff", None)
    profile = getattr(u, "doctor_profile", None)
    if staff is not None:
        hospital = staff.hospital.name
    elif profile is not None:
        hospital = profile.hospital.name
    return {
        "id": u.id,
        "username": u.username,
        "name": f"{u.first_name} {u.last_name}".strip(),
        "email": u.email,
        "mobile": u.mobile,
        "role": "ADMIN" if u.is_superuser else u.role,
        "is_active": u.is_active,
        "date_joined": u.date_joined.isoformat(),
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "hospital": hospital,
        "appointments": getattr(u, "appointment_count", 0),
    }


class UserListView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get(self, request):
        qs = (
            User.objects.annotate(appointment_count=Count("appointments", distinct=True))
            .select_related("hospital_staff__hospital", "doctor_profile__hospital")
            .order_by("-date_joined", "-id")
        )
        role = request.query_params.get("role")
        if role in dict(User.ROLE_CHOICES):
            qs = qs.filter(role=role)
        active = request.query_params.get("active")
        if active in ("true", "false"):
            qs = qs.filter(is_active=(active == "true"))
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
                | Q(first_name__icontains=search) | Q(last_name__icontains=search)
                | Q(mobile__icontains=search)
            )

        page_size = _int(request.query_params.get("page_size"), 20, 5, 100)
        paginator = Paginator(qs, page_size)
        try:
            page = paginator.page(_int(request.query_params.get("page"), 1, 1, 100000))
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
        return Response({
            "count": paginator.count,
            "page": page.number,
            "pages": paginator.num_pages,
            "results": [_user_row(u) for u in page.object_list],
        })


class UserDetailView(APIView):
    permission_classes = [IsApplicationAdmin]

    def _target(self, request, pk):
        """Returns (user, error_response)."""
        target = (
            User.objects.annotate(appointment_count=Count("appointments", distinct=True))
            .select_related("hospital_staff__hospital", "doctor_profile__hospital")
            .filter(pk=pk).first()
        )
        if not target:
            return None, Response({"detail": "User not found."}, status=404)
        if target.pk == request.user.pk:
            return None, Response({"detail": "You cannot change your own account here."}, status=400)
        if target.is_superuser or target.role == User.ROLE_ADMIN:
            return None, Response({"detail": "Application Admin accounts cannot be changed here."}, status=403)
        return target, None

    def patch(self, request, pk):
        target, error = self._target(request, pk)
        if error:
            return error
        active = request.data.get("is_active")
        if not isinstance(active, bool):
            return Response({"is_active": ["Send true or false."]}, status=400)
        target.is_active = active
        target.save(update_fields=["is_active"])
        if target.role == User.ROLE_DOCTOR:
            DoctorProfile.objects.filter(user=target).update(is_active=active)
        return Response(_user_row(target))

    def delete(self, request, pk):
        target, error = self._target(request, pk)
        if error:
            return error
        staff = getattr(target, "hospital_staff", None)
        if staff is not None and staff.staff_role == HospitalStaff.ROLE_ADMIN:
            return Response(
                {"detail": "This is a hospital admin account. Deactivate it instead of deleting it."}, status=409
            )
        try:
            target.delete()
        except ProtectedError:
            return Response(
                {"detail": "This user has appointment history and cannot be deleted. Deactivate the account instead."},
                status=409,
            )
        return Response(status=204)
# ======================================================================
# Bell notifications: hospitals waiting for approval
# ======================================================================
class NotificationView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get(self, request):
        pending = Hospital.objects.filter(status=Hospital.STATUS_PENDING).order_by("-created_at", "-id")
        return Response({
            "pending_count": pending.count(),
            "pending_hospitals": [
                {
                    "id": h.id, "name": h.name, "city": h.city,
                    "registration_number": h.registration_number, "created_at": h.created_at.isoformat(),
                }
                for h in pending[:10]
            ],
        })
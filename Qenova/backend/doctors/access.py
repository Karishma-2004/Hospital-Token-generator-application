"""Central place for 'who is allowed to do what' so every view uses the same rules.

All write endpoints are protected by JWT (DRF default auth = simplejwt) AND one of
these permission classes. The role claim inside the token is informational only;
authorisation is always re-checked against the database.
"""
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions

from accounts.models import User
from .models import Hospital, HospitalStaff


def is_application_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == User.ROLE_ADMIN))


def get_membership(user):
    if not (user and user.is_authenticated) or user.role != User.ROLE_RECEPTIONIST:
        return None
    try:
        return user.hospital_staff
    except ObjectDoesNotExist:
        return None


def get_staff_hospital(user, approved_only=True):
    membership = get_membership(user)
    if not membership:
        return None
    hospital = membership.hospital
    if approved_only and hospital.status != Hospital.STATUS_APPROVED:
        return None
    return hospital


class IsApplicationAdmin(permissions.BasePermission):
    message = "Application Admin access required."

    def has_permission(self, request, view):
        return is_application_admin(request.user)


class IsHospitalStaff(permissions.BasePermission):
    """Hospital admin OR receptionist of an APPROVED hospital."""
    message = "Hospital staff access required (hospital must be approved)."

    def has_permission(self, request, view):
        hospital = get_staff_hospital(request.user)
        if hospital is None:
            return False
        request.hospital = hospital
        request.staff_role = request.user.hospital_staff.staff_role
        return True


class IsHospitalAdmin(IsHospitalStaff):
    message = "Only the hospital admin can do this."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.staff_role == HospitalStaff.ROLE_ADMIN

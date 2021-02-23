from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class VerificationPermission(BasePermission):
    manage_verification = translations.permissions["manage_verification"]

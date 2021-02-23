from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class BeTheProfessionalCog(BasePermission):
    btp_manage = translations.permissions["btp_manage"]

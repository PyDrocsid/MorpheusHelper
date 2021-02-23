from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class NewsPermission(BasePermission):
    news_manage = translations.permissions["news_manage"]

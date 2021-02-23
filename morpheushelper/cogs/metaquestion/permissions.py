from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class MetaQuestionPermission(BasePermission):
    mq_reduce = translations.permissions["mq_reduce"]

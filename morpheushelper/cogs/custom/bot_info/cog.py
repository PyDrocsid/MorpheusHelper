from cogs.library import BotInfoCog


class CustomBotInfoCog(BotInfoCog, name="Bot Information"):
    def __init__(self):
        super().__init__(info_icon="https://github.com/PyDrocsid.png")

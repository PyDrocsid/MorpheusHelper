from discord import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context


class MetaQuestionCog(Cog, name="Metafragen"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="metafrage", aliases=["meta", "metaquestion"])
    async def metaquestion(self, ctx: Context):
        """
        display information about meta questions
        """

        embed = Embed(title="Metafragen", url="http://metafrage.de/")
        embed.description = (
            "Eine Metafrage ist eine Frage über eine Frage, wie beispielsweise „Darf ich etwas fragen?“ "
            "oder „Kennt sich jemand mit Computern aus?“.\n\nIn der Regel wird der Begriff Metafrage "
            "aber verallgemeinert und damit alle Fragen bezeichnet, die keine direkte Frage zum Problem "
            "des Hilfesuchenden sind. Der Hilfesuchende fragt also zunächst allgemein, ob jemand helfen "
            "kann. Gerade Neulinge oder unerfahrene Benutzer lassen sich zu Metafragen hinreißen, um "
            "einen kompetenten und hilfsbereiten Ansprechpartner zu finden. Meistens werden Metafragen "
            "ignoriert oder der Fragende wird rüde darauf hingewiesen, dass ihm niemand bei seinem Problem "
            "helfen könne, ohne dies zu kennen. Grundsätzlich folgt auf eine Meta-Frage eine weitere Frage."
        )
        embed.add_field(
            name="Vorteile von Metafragen",
            value=(
                "- als höfliche Floskel um Aufmerksamkeit zu gewinnen\n"
                "- Beginn einer zunächst einseitigen Konversation (Allgemeine Problemanalyse)"
            ),
            inline=False,
        )
        embed.add_field(
            name="Nachteile von Metafragen",
            value=(
                "- die Anwesenden könnten eventuell bei dem Problem helfen, obwohl sie (eventuell aus Bescheidenheit)"
                " nicht von sich behaupten würden, mit dem Thema vertraut zu sein,\n"
                "- oft ist die Metafrage falsch formuliert, z. B. wird gefragt „kennt sich jemand mit Kochen aus?“ "
                "und er will nur wissen, ob Mangos essbar sind,\n"
                "- Auch wenn jemand mit dem erfragten Thema vertraut ist, bedeutet dies nicht, dass er eine spezielle"
                " Frage zu diesem beantworten kann – niemand ist allwissend,\n"
                "- wenn keine Reaktion auf die Metafrage erfolgt, beläßt es der Fragende meist dabei. So kann eine"
                " Antwort auf das Problem von später aufmerksam Werdenden nicht erfolgen.\n"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

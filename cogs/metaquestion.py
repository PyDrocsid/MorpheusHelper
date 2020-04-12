import re

from discord import Embed, Member, RawReactionActionEvent, TextChannel, Message
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only

from util import check_access

WASTEBASKET = b"\xf0\x9f\x97\x91\xef\xb8\x8f".decode()


def make_embed(requested_by: Member) -> Embed:
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
    embed.set_footer(text=f"Requested by @{requested_by} ({requested_by.id})", icon_url=requested_by.avatar_url)
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
    return embed


class MetaQuestionCog(Cog, name="Metafragen"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_raw_reaction_add(self, event: RawReactionActionEvent):
        if event.member == self.bot.user:
            return

        channel: TextChannel = self.bot.get_channel(event.channel_id)
        message: Message = await channel.fetch_message(event.message_id)
        member: Member = channel.guild.get_member(event.user_id)
        if event.emoji.name == "metaquestion":
            if message.author == self.bot.user or not channel.permissions_for(member).send_messages:
                await message.remove_reaction(event.emoji, member)
                return

            for reaction in message.reactions:
                if reaction.emoji == event.emoji:
                    if reaction.me:
                        return
                    break
            await message.add_reaction(event.emoji)
            msg: Message = await channel.send(message.author.mention, embed=make_embed(event.member))
            await msg.add_reaction(WASTEBASKET)
        elif event.emoji.name == WASTEBASKET:
            for embed in message.embeds:
                if (match := re.match(r"^Requested by @.*?#\d{4} \((\d+)\)$", embed.footer.text)) is not None:
                    author_id = int(match.group(1))
                    if author_id == event.member.id or await check_access(event.member):
                        break
            else:
                await message.remove_reaction(event.emoji, member)
                return

            await message.delete()

    @commands.command(name="metafrage", aliases=["meta", "metaquestion"])
    @guild_only()
    async def metaquestion(self, ctx: Context):
        """
        display information about meta questions
        """

        message: Message = await ctx.send(embed=make_embed(ctx.author))
        await message.add_reaction(WASTEBASKET)

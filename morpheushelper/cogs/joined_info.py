from datetime import datetime

from PyDrocsid.database import db_thread, db
from PyDrocsid.translations import translations
from discord import Member
from discord.ext import commands
from discord.ext.commands import Cog, Context, Bot, guild_only

from models.mod import Join
from dateutil.relativedelta import relativedelta


def date_diff_to_str(date1: datetime, date2: datetime):
    rd = relativedelta(date1, date2)
    if rd.years:
        return translations.f_joined_years(rd.years)
    if rd.months:
        return translations.f_joined_months(rd.months)
    if rd.weeks:
        return translations.f_joined_weeks(rd.weeks)
    return translations.joined_days


class JoinedInfoCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command()
    @guild_only()
    async def joined(self, ctx: Context, user: Member = None):
        """
        Returns the date on which the user joined the server
        """
        if not user:
            user = ctx.author
        join_query = await db_thread(lambda: db.query(Join).filter(Join.member == user.id)
                                     .order_by(Join.timestamp).first())
        first_join = user.joined_at
        if join_query:
            first_join = join_query.timestamp

        await ctx.send(date_diff_to_str(datetime.today(), first_join))

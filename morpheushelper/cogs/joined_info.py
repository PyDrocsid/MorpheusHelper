from datetime import datetime

from PyDrocsid.database import db_thread, db
from PyDrocsid.translations import translations
from discord import Member, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Context, Bot, guild_only

from models.mod import Join, Kick
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
        last_auto_kick = await db_thread(lambda: db.query(Kick).filter_by(member=user.id, mod=None)
                                         .order_by(Kick.timestamp.desc()).first())
        last_join_after_kick = await db_thread(lambda: db.query(Join).filter(Join.member == user.id)
                                               .order_by(Join.timestamp.desc()).first().timestamp)
        if last_auto_kick:
            last_join_after_kick = await db_thread(
                lambda: db.query(Join).filter(Join.timestamp > last_auto_kick.timestamp,
                                              Join.member == user.id).order_by(Join.timestamp.asc()).first().timestamp)
        embed = Embed(title=translations.joined_info,
                      description=f"{user.mention} {date_diff_to_str(datetime.today(), last_join_after_kick)}")
        await ctx.send(embed=embed)

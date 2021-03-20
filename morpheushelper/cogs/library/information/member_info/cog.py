from datetime import datetime

from dateutil.relativedelta import relativedelta
from discord import Member, Embed
from discord.ext import commands
from discord.ext.commands import Context, guild_only

from PyDrocsid.cog import Cog
from PyDrocsid.database import db_thread, db
from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t
from ...contributor import Contributor
from ...moderation import ModCog
from ...moderation.mod.models import Kick, Join

tg = t.g
t = t.member_info


def date_diff_to_str(date1: datetime, date2: datetime):
    rd = relativedelta(date1, date2)
    if rd.years:
        return t.joined_years(cnt=rd.years)
    if rd.months:
        return t.joined_months(cnt=rd.months)
    if rd.weeks:
        return t.joined_weeks(cnt=rd.weeks)
    return t.joined_days


class MemberInfoCog(Cog, name="Member Information"):
    CONTRIBUTORS = [Contributor.Florian, Contributor.Defelo]
    PERMISSIONS = BasePermission
    DEPENDENCIES = [ModCog]

    @classmethod
    async def get_relevant_join(cls, member: Member) -> datetime:
        last_auto_kick = await db_thread(
            lambda: db.query(Kick, member=member.id, mod=None).order_by(Kick.timestamp.desc()).first()
        )
        if last_auto_kick:
            relevant_join = await db_thread(
                lambda: db.query(Join, member=member.id)
                .filter(Join.timestamp > last_auto_kick.timestamp)
                .order_by(Join.timestamp.asc())
                .first()
            )
        else:
            relevant_join = await db_thread(
                lambda: db.query(Join, member=member.id).order_by(Join.timestamp.asc()).first()
            )

        if relevant_join is None:
            relevant_join = member.joined_at
        else:
            relevant_join = relevant_join.timestamp

        return relevant_join

    @commands.command()
    @guild_only()
    async def joined(self, ctx: Context, member: Member = None):
        """
        Returns a rough estimate for the user's time on the server
        """

        member = member or ctx.author
        relevant_join: datetime = await self.get_relevant_join(member)

        embed = Embed(
            title=t.member_info,
            description=f"{member.mention} {date_diff_to_str(datetime.today(), relevant_join)}",
        )
        await ctx.send(embed=embed)

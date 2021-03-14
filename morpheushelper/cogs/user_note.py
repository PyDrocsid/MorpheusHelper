from PyDrocsid.database import db_thread, db
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.translations import translations
from discord import Member, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Context, UserInputError, guild_only

from models.user_note import UserNote
from permissions import Permission


class UserNoteCog(Cog):
    @commands.group(name="user_notes")
    @guild_only()
    async def user_notes(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            raise UserInputError

    @user_notes.command(name="add")
    @Permission.user_notes.check
    async def add(self, ctx: Context, member: Member, description: str):
        """
        Add notes for a user
        """
        await db_thread(UserNote.create, member.id, description)
        await ctx.message.add_reaction(name_to_emoji["white_check_mark"])

    @user_notes.command(name="show")
    @Permission.user_notes.check
    async def show(self, ctx: Context, member: Member):
        """
        Return saved notes
        """
        notes = await db_thread(lambda: db.query(UserNote).filter(UserNote.member == member.id))
        user_notes = ""
        for note in notes:
            user_notes += f"\n{note.description} {note.timestamp.strftime('%d.%m.%Y')}"
        await ctx.send(embed=Embed(title=translations.user_notes, description=user_notes))

from typing import Mapping, Union, List

import discord
from discord import Reaction, Member, User, Embed, Emoji, Role
from discord.ext import commands
from discord.ext.commands import Cog, Context

from database import run_in_thread
from models.settings import Settings
from models.helper_scores import HelperScores
from models.helper_roles import HelperRoles

DEFAULT_EMOJI = chr(int("1f44d", 16))  # :thumbsup:


class HelperRole():
    def __init__(self, *, score, role):
        self.score = score
        self.role = role


async def set_reaction(emoji: str) -> str:
    return await run_in_thread(Settings.set, str, "score_reaction", emoji)

async def get_reaction() -> str:
    return await run_in_thread(Settings.get, str, "score_reaction", DEFAULT_EMOJI)

async def get_user(user_id: int) -> HelperScores:
    return await run_in_thread(HelperScores.get, user_id)

async def set_score(user_id: int, score: int) -> HelperScores:
    return await run_in_thread(HelperScores.set, user_id, score)

async def add_role(role_id: int, score: int) -> HelperRoles:
    return await run_in_thread(HelperRoles.set, role_id, score)

async def remove_role(role_id: int) -> bool:
    return await run_in_thread(HelperRoles.remove, role_id)

async def get_roles(guild) -> List[HelperRole]:
    rows = await run_in_thread(HelperRoles.all)
    scores = { r.role_id: r.score for r in rows }
    
    roles = list(filter(lambda row: row.id in scores, guild.roles))

    helper_roles = [ HelperRole(score=scores[r.id], role=r) for r in roles ] 

    return helper_roles


class HelperSystemCog(Cog, name="HelperSystem"):
    @Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: Union[Member, User]):
        score_reaction: str = await get_reaction()
        if str(reaction) != score_reaction:
            return

        # Increment score

        helper = reaction.message.author

        row = await get_user(helper.id)
        score = row.score + 1
        await set_score(helper.id, score)

        # Update roles

        roles = await get_roles(user.guild)

        try:
            await helper.remove_roles(*[ r.role for r in roles ])
        except discord.errors.Forbidden:
            pass

        new_score = 0
        new_role = None
        for role in roles:
            if row.score >= role.score > new_score:
                new_role = role
                new_score = role.score

        await helper.add_roles(new_role.role)

    @commands.group(name="helper")
    async def helper(self, ctx: Context):
        """manage HelperSystem"""

    @helper.command()
    async def info(self, ctx: Context, user: User = None):
        """display a user's helper profile"""

        if user is None:
            user = ctx.message.author

        row = await get_user(user.id)

        full_name = f"{user.name}#{user.discriminator}"

        embed = Embed(title=self.qualified_name) \
        .add_field(name="User", value=full_name, inline=False)\
        .add_field(name="Score", value=row.score) \
        .add_field(name="Role", value="little-helper")

        await ctx.send(embed=embed)

    @helper.command()
    async def reaction(self, ctx: Context, emoji: Union[Emoji, str] = None):
        """set or print the reaction emoji"""
        
        if emoji is not None:
            await set_reaction(emoji)
        else:
            emoji = await get_reaction()

        embed = Embed(title=self.qualified_name,
        description=f"Reaction emoji: {emoji}")

        await ctx.send(embed=embed)

    @helper.group(name="roles")
    async def roles(self, ctx: Context):
        """manage roles"""
        if ctx.invoked_subcommand:
            return
            
        roles = await get_roles(ctx.guild)

        embed = Embed(title=self.qualified_name,
        description="Helper Roles") \
        .add_field(name="Reaction", value="\n".join((str(r.role.name) for r in roles))) \
        .add_field(name="Score", value="\n".join((str(r.score) for r in roles)))

        await ctx.send(embed=embed)

    @roles.command()
    async def set(self, ctx: Context, role: Role, score: int):
        """set a role's score"""
        await add_role(role.id, score)
        await ctx.send(f"New score for {role}: {score}")

    @roles.command()
    async def remove(self, ctx: Context, role: Role):
        if await remove_role(role.id):
            ctx.send(f"Role {role} removed")
        else:
            ctx.send("Nothing to remove")
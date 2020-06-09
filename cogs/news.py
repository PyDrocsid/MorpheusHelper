import io
from typing import Optional

from discord import Member, TextChannel, Role, Guild, File, HTTPException, Forbidden
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.news_authorization import NewsAuthorization
from translations import translations
from util import permission_level, send_to_changelog, read_normal_message, MODERATOR


class NewsCog(Cog, name="News"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(name="news")
    @guild_only()
    async def news(self, ctx: Context):
        """
        manage news channels
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(NewsCog.news)

    @news.group(name="auth", aliases=["a"])
    @permission_level(MODERATOR)
    async def auth(self, ctx: Context):
        """
        manage authorized users and channels
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(NewsCog.auth)

    @auth.command(name="list", aliases=["l", "?"])
    async def list_auth(self, ctx: Context):
        """
        list authorized users and channels
        """

        out = []
        guild: Guild = ctx.guild
        for authorization in await run_in_thread(db.all, NewsAuthorization):
            text_channel: Optional[TextChannel] = guild.get_channel(authorization.channel_id)
            member: Optional[Member] = guild.get_member(authorization.user_id)
            if text_channel is None or member is None:
                await run_in_thread(db.delete, authorization)
                continue
            line = f"- `@{member}` -> {text_channel.mention}"
            if authorization.notification_role_id is not None:
                role: Optional[Role] = guild.get_role(authorization.notification_role_id)
                if role is None:
                    await run_in_thread(db.delete, authorization)
                    continue
                line += f" (`@{role}`)"
            out.append(line)
        if out:
            await ctx.send("\n".join(out))
        else:
            await ctx.send(translations.no_news_authorizations)

    @auth.command(name="add", aliases=["a", "+"])
    async def auth_add(self, ctx: Context, user: Member, channel: TextChannel, notification_role: Optional[Role]):
        """
        authorize a new user to send news to a specific channel
        """

        if await run_in_thread(db.first, NewsAuthorization, user_id=user.id, channel_id=channel.id) is not None:
            raise CommandError(translations.news_already_authorized)
        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.news_not_added_no_permissions)

        role_id = notification_role.id if notification_role is not None else None

        await run_in_thread(NewsAuthorization.create, user.id, channel.id, role_id)
        await ctx.send(translations.news_authorized)
        await send_to_changelog(ctx.guild, translations.f_log_news_authorized(user.mention, channel.mention))

    @auth.command(name="remove", aliases=["del", "r", "d", "-"])
    async def auth_del(self, ctx: Context, user: Member, channel: TextChannel):
        """
        remove user authorization
        """

        authorization: Optional[NewsAuthorization] = await run_in_thread(
            db.first, NewsAuthorization, user_id=user.id, channel_id=channel.id
        )
        if authorization is None:
            raise CommandError(translations.news_not_authorized)

        await run_in_thread(db.delete, authorization)
        await ctx.send(translations.news_unauthorized)
        await send_to_changelog(ctx.guild, translations.f_log_news_unauthorized(user.mention, channel.mention))

    @news.command(name="send", aliases=["s"])
    async def send(self, ctx: Context, channel: TextChannel, *, message: Optional[str]):
        """
        send a news message
        """

        authorization: Optional[NewsAuthorization] = await run_in_thread(
            db.first, NewsAuthorization, user_id=ctx.author.id, channel_id=channel.id
        )
        if authorization is None:
            raise CommandError(translations.news_you_are_not_authorized)

        if message is None:
            message = ""

        if not message and not ctx.message.attachments:
            await ctx.send(translations.send_message)
            message, files = await read_normal_message(self.bot, ctx.channel, ctx.author)
        else:
            files = []
            for attachment in ctx.message.attachments:
                file = io.BytesIO()
                await attachment.save(file)
                files.append(File(file, filename=attachment.filename, spoiler=attachment.is_spoiler()))

        if authorization.notification_role_id is not None:
            role: Optional[Role] = ctx.guild.get_role(authorization.notification_role_id)
            if role is not None:
                message = role.mention + " " + message

        try:
            await channel.send(content=message, files=files)
        except (HTTPException, Forbidden):
            raise CommandError(translations.msg_could_not_be_sent)
        else:
            await ctx.send(translations.msg_sent)

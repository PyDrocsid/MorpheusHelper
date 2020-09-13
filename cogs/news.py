import re
from typing import Optional, Union

from PyDrocsid.database import db_thread, db
from PyDrocsid.translations import translations
from PyDrocsid.util import send_long_embed, read_normal_message, attachment_to_file
from discord import Member, TextChannel, Role, Guild, HTTPException, Forbidden, Embed, Color
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, UserInputError

from colours import Colours
from models.news_authorization import NewsAuthorization
from permissions import Permission
from util import send_to_changelog


class NewsCog(Cog, name="News"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group()
    @guild_only()
    async def news(self, ctx: Context):
        """
        manage news channels
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @news.group(name="auth", aliases=["a"])
    @Permission.news_manage.check
    async def news_auth(self, ctx: Context):
        """
        manage authorized users and channels
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @news_auth.command(name="list", aliases=["l", "?"])
    async def news_auth_list(self, ctx: Context):
        """
        list authorized users and channels
        """

        out = []
        guild: Guild = ctx.guild
        for authorization in await db_thread(db.all, NewsAuthorization):
            text_channel: Optional[TextChannel] = guild.get_channel(authorization.channel_id)
            member: Optional[Member] = guild.get_member(authorization.user_id)
            if text_channel is None or member is None:
                await db_thread(db.delete, authorization)
                continue
            line = f":small_orange_diamond: {member.mention} -> {text_channel.mention}"
            if authorization.notification_role_id is not None:
                role: Optional[Role] = guild.get_role(authorization.notification_role_id)
                if role is None:
                    await db_thread(db.delete, authorization)
                    continue
                line += f" ({role.mention})"
            out.append(line)
        embed = Embed(title=translations.news, colour=Colours.News)
        if out:
            embed.description = "\n".join(out)
        else:
            embed.colour = Colours.error
            embed.description = translations.no_news_authorizations
        await send_long_embed(ctx, embed)

    @news_auth.command(name="add", aliases=["a", "+"])
    async def news_auth_add(self, ctx: Context, user: Member, channel: TextChannel, notification_role: Optional[Role]):
        """
        authorize a new user to send news to a specific channel
        """

        if await db_thread(db.first, NewsAuthorization, user_id=user.id, channel_id=channel.id) is not None:
            raise CommandError(translations.news_already_authorized)
        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.news_not_added_no_permissions)

        role_id = notification_role.id if notification_role is not None else None

        await db_thread(NewsAuthorization.create, user.id, channel.id, role_id)
        embed = Embed(title=translations.news, colour=Colours.News, description=translations.news_authorized)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_news_authorized(user.mention, channel.mention))

    @news_auth.command(name="remove", aliases=["del", "r", "d", "-"])
    async def news_auth_remove(self, ctx: Context, user: Member, channel: TextChannel):
        """
        remove user authorization
        """

        authorization: Optional[NewsAuthorization] = await db_thread(
            db.first, NewsAuthorization, user_id=user.id, channel_id=channel.id
        )
        if authorization is None:
            raise CommandError(translations.news_not_authorized)

        await db_thread(db.delete, authorization)
        embed = Embed(title=translations.news, colour=Colours.News, description=translations.news_unauthorized)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_news_unauthorized(user.mention, channel.mention))

    @news.command(name="send", aliases=["s"])
    async def news_send(self, ctx: Context, channel: TextChannel, color: Optional[Union[Color, str]] = None, *,
                        message: Optional[str]):
        """
        send a news message
        """

        authorization: Optional[NewsAuthorization] = await db_thread(
            db.first, NewsAuthorization, user_id=ctx.author.id, channel_id=channel.id
        )
        if authorization is None:
            raise CommandError(translations.news_you_are_not_authorized)

        if isinstance(color, str):
            if not re.match(r"^[0-9a-fA-F]{6}$", color):
                raise CommandError(translations.invalid_color)
            color = int(color, 16)

        if message is None:
            message = ""

        embed = Embed(title=translations.news, colour=Colours.News, description="")
        if not message and not ctx.message.attachments:
            embed.description = translations.send_message
            await ctx.send(embed=embed)
            message, files = await read_normal_message(self.bot, ctx.channel, ctx.author)
        else:
            files = [await attachment_to_file(attachment) for attachment in ctx.message.attachments]

        content = ""
        send_embed = Embed(title=translations.news, description=message, colour=Colours.News)
        send_embed.set_footer(text=translations.f_sent_by(ctx.author, ctx.author.id), icon_url=ctx.author.avatar_url)

        if authorization.notification_role_id is not None:
            role: Optional[Role] = ctx.guild.get_role(authorization.notification_role_id)
            if role is not None:
                content = role.mention

        if color is not None:
            send_embed.colour = color

        if files:
            send_embed.set_image(url="attachment://" + files[0].filename)

        try:
            await channel.send(content=content, embed=send_embed, files=files)
        except (HTTPException, Forbidden):
            raise CommandError(translations.msg_could_not_be_sent)
        else:
            embed.description = translations.msg_sent
            await ctx.send(embed=embed)

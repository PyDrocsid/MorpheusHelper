from datetime import datetime
from typing import Optional, List

import requests
from PyDrocsid.database import db_thread, db
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import Embed, TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, UserInputError

from colours import Colours
from info import VERSION
from models.reddit import RedditPost, RedditChannel
from permissions import Permission
from util import send_to_changelog

import logging


def exists_subreddit(subreddit: str) -> bool:
    return requests.head(
        f"https://www.reddit.com/r/{subreddit}/hot.json", headers={"User-agent": f"MorpheusHelper/{VERSION}"}
    ).ok


def get_subreddit_name(subreddit: str) -> str:
    return requests.get(
        f"https://www.reddit.com/r/{subreddit}/about.json", headers={"User-agent": f"MorpheusHelper/{VERSION}"}
    ).json()["data"]["display_name"]


def fetch_reddit_posts(subreddit: str, limit: int) -> List[dict]:
    response = requests.get(
        f"https://www.reddit.com/r/{subreddit}/hot.json",
        headers={"User-agent": f"MorpheusHelper/{VERSION}"},
        params={"limit": str(limit)},
    )

    if not response.ok:
        logging.warning("could not fetch reddit posts of r/%s %s %s", subreddit, response, response.status_code)
        return []

    posts: List[dict] = []
    for post in response.json()["data"]["children"]:
        # t3 = link
        if post["kind"] == "t3" and post["data"].get("post_hint") == "image":
            posts.append(
                {
                    "id": post["data"]["id"],
                    "author": post["data"]["author"],
                    "title": post["data"]["title"],
                    "created_utc": post["data"]["created_utc"],
                    "score": post["data"]["score"],
                    "num_comments": post["data"]["num_comments"],
                    "permalink": post["data"]["permalink"],
                    "url": post["data"]["url"],
                    "subreddit": post["data"]["subreddit"],
                }
            )
    return posts


def create_embed(post: dict) -> Embed:
    embed = Embed(
        title=post["title"],
        url=f"https://reddit.com{post['permalink']}",
        description=f"{post['score']} :thumbsup: \u00B7 {post['num_comments']} :speech_balloon:",
        colour=Colours.Reddit,  # Reddit's brand color
    )
    embed.set_author(name=f"u/{post['author']}", url=f"https://reddit.com/u/{post['author']}")
    embed.set_image(url=post["url"])
    embed.set_footer(text=f"r/{post['subreddit']}")
    embed.timestamp = datetime.utcfromtimestamp(post["created_utc"])
    return embed


class RedditCog(Cog, name="Reddit"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_ready(self):
        interval = await Settings.get(int, "reddit_interval", 4)
        await self.start_loop(interval)

    @tasks.loop()
    async def reddit_loop(self):
        await self.pull_hot_posts()

    async def pull_hot_posts(self):
        logging.info("pulling hot reddit posts")
        limit = await Settings.get(int, "reddit_limit", 4)
        for reddit_channel in await db_thread(db.all, RedditChannel):  # type: RedditChannel
            text_channel: Optional[TextChannel] = self.bot.get_channel(reddit_channel.channel)
            if text_channel is None:
                await db_thread(db.delete, reddit_channel)
                continue

            for post in fetch_reddit_posts(reddit_channel.subreddit, limit):
                if await db_thread(RedditPost.post, post["id"]):
                    await text_channel.send(embed=create_embed(post))

        await db_thread(RedditPost.clean)

    async def start_loop(self, interval):
        self.reddit_loop.cancel()
        self.reddit_loop.change_interval(hours=interval)
        try:
            self.reddit_loop.start()
        except RuntimeError:
            self.reddit_loop.restart()

    @commands.group()
    @Permission.manage_reddit.check
    @guild_only()
    async def reddit(self, ctx: Context):
        """
        manage reddit integration
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=translations.reddit, colour=Colours.Reddit)

        interval = await Settings.get(int, "reddit_interval", 4)
        embed.add_field(name=translations.interval, value=translations.f_x_hours(interval))

        limit = await Settings.get(int, "reddit_limit", 4)
        embed.add_field(name=translations.limit, value=str(limit))

        out = []
        for reddit_channel in await db_thread(db.all, RedditChannel):  # type: RedditChannel
            text_channel: Optional[TextChannel] = self.bot.get_channel(reddit_channel.channel)
            if text_channel is None:
                await db_thread(db.delete, reddit_channel)
            else:
                sub = reddit_channel.subreddit
                out.append(f":small_orange_diamond: [r/{sub}](https://reddit.com/r/{sub}) -> {text_channel.mention}")
        embed.add_field(
            name=translations.reddit_links, value="\n".join(out) or translations.no_reddit_links, inline=False
        )

        await ctx.send(embed=embed)

    @reddit.command(name="add", aliases=["a", "+"])
    async def reddit_add(self, ctx: Context, subreddit: str, channel: TextChannel):
        """
        create a link between a subreddit and a channel
        """

        if not exists_subreddit(subreddit):
            raise CommandError(translations.subreddit_not_found)
        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.reddit_link_not_created_permission)

        subreddit = get_subreddit_name(subreddit)
        if await db_thread(db.first, RedditChannel, subreddit=subreddit, channel=channel.id) is not None:
            raise CommandError(translations.reddit_link_already_exists)

        await db_thread(RedditChannel.create, subreddit, channel.id)
        embed = Embed(title=translations.reddit, colour=Colours.Reddit, description=translations.reddit_link_created)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_reddit_link_created(subreddit, channel.mention))

    @reddit.command(name="remove", aliases=["r", "del", "d", "-"])
    async def reddit_remove(self, ctx: Context, subreddit: str, channel: TextChannel):
        """
        remove a reddit link
        """

        subreddit = get_subreddit_name(subreddit)
        link: Optional[RedditChannel] = await db_thread(
            db.first, RedditChannel, subreddit=subreddit, channel=channel.id
        )
        if link is None:
            raise CommandError(translations.reddit_link_not_found)

        await db_thread(db.delete, link)
        embed = Embed(title=translations.reddit, colour=Colours.Reddit, description=translations.reddit_link_removed)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_reddit_link_removed(subreddit, channel.mention))

    @reddit.command(name="interval", aliases=["int", "i"])
    async def reddit_interval(self, ctx: Context, hours: int):
        """
        change lookup interval (in hours)
        """

        if not 0 < hours < (1 << 31):
            raise CommandError(translations.invalid_interval)

        await Settings.set(int, "reddit_interval", hours)
        await self.start_loop(hours)
        embed = Embed(title=translations.reddit, colour=Colours.Reddit, description=translations.reddit_interval_set)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_reddit_interval_set(hours))

    @reddit.command(name="limit", aliases=["lim"])
    async def reddit_limit(self, ctx: Context, limit: int):
        """
        change limit of posts to be sent concurrently
        """

        if not 0 < limit < (1 << 31):
            raise CommandError(translations.invalid_limit)

        await Settings.set(int, "reddit_limit", limit)
        embed = Embed(title=translations.reddit, colour=Colours.Reddit, description=translations.reddit_limit_set)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_reddit_limit_set(limit))

    @reddit.command(name="trigger", aliases=["t"])
    async def reddit_trigger(self, ctx: Context):
        """
        pull hot posts now and reset the timer
        """

        await self.start_loop(await Settings.get(int, "reddit_interval", 4))
        embed = Embed(title=translations.reddit, colour=Colours.Reddit, description=translations.done)
        await ctx.send(embed=embed)

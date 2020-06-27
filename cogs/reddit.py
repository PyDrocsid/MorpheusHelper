from datetime import datetime
from typing import Optional, List

import requests
from discord import Embed, TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from info import VERSION
from models.reddit import RedditPost, RedditChannel
from models.settings import Settings
from permission import Permission
from translations import translations
from util import permission_level, send_to_changelog


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
        print(f"could not fetch reddit posts of r/{subreddit}")
        return []

    posts: List[dict] = []
    for post in response.json()["data"]["children"]:
        # t3 = link
        if post["kind"] == "t3" and post["data"]["post_hint"] == "image":
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
        color=0xFF4500,  # Reddit's brand color
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
        interval = await run_in_thread(Settings.get, int, "reddit_interval", 4)
        await self.start_loop(interval)
        return True

    @tasks.loop()
    async def reddit_loop(self):
        await self.pull_hot_posts()

    async def pull_hot_posts(self):
        print("pulling hot reddit posts")
        limit = await run_in_thread(Settings.get, int, "reddit_limit", 4)
        for reddit_channel in await run_in_thread(db.all, RedditChannel):  # type: RedditChannel
            text_channel: Optional[TextChannel] = self.bot.get_channel(reddit_channel.channel)
            if text_channel is None:
                await run_in_thread(db.delete, reddit_channel)
                continue

            for post in fetch_reddit_posts(reddit_channel.subreddit, limit):
                if await run_in_thread(RedditPost.post, post["id"]):
                    await text_channel.send(embed=create_embed(post))

        await run_in_thread(RedditPost.clean)

    async def start_loop(self, interval):
        self.reddit_loop.cancel()
        self.reddit_loop.change_interval(hours=interval)
        try:
            self.reddit_loop.start()
        except RuntimeError:
            self.reddit_loop.restart()

    @commands.group(name="reddit")
    @permission_level(Permission.manage_reddit)
    @guild_only()
    async def reddit(self, ctx: Context):
        """
        manage reddit integration
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(RedditCog.reddit)

    @reddit.command(name="list", aliases=["l", "?"])
    async def lst(self, ctx: Context):
        """
        list reddit links
        """

        out = []
        for reddit_channel in await run_in_thread(db.all, RedditChannel):  # type: RedditChannel
            text_channel: Optional[TextChannel] = self.bot.get_channel(reddit_channel.channel)
            if text_channel is None:
                await run_in_thread(db.delete, reddit_channel)
                continue
            out.append(f"`r/{reddit_channel.subreddit}` -> {text_channel.mention}")

        if not out:
            await ctx.send(translations.no_reddit_channels)
        else:
            await ctx.send("\n".join(out))

    @reddit.command(name="add", aliases=["a", "+"])
    async def add(self, ctx: Context, subreddit: str, channel: TextChannel):
        """
        create a link between a subreddit and a channel
        """

        if not exists_subreddit(subreddit):
            raise CommandError(translations.subreddit_not_found)
        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.reddit_link_not_created_permission)

        subreddit = get_subreddit_name(subreddit)
        if await run_in_thread(db.first, RedditChannel, subreddit=subreddit, channel=channel.id) is not None:
            raise CommandError(translations.reddit_link_already_exists)

        await run_in_thread(RedditChannel.create, subreddit, channel.id)
        await ctx.send(translations.reddit_link_created)
        await send_to_changelog(ctx.guild, translations.f_log_reddit_link_created(subreddit, channel.mention))

    @reddit.command(name="remove", aliases=["r", "del", "d", "-"])
    async def remove(self, ctx: Context, subreddit: str, channel: TextChannel):
        """
        remove a reddit link
        """

        subreddit = get_subreddit_name(subreddit)
        link: Optional[RedditChannel] = await run_in_thread(
            db.first, RedditChannel, subreddit=subreddit, channel=channel.id
        )
        if link is None:
            raise CommandError(translations.reddit_link_not_found)

        await run_in_thread(db.delete, link)
        await ctx.send(translations.reddit_link_removed)
        await send_to_changelog(ctx.guild, translations.f_log_reddit_link_removed(subreddit, channel.mention))

    @reddit.command(name="interval", aliases=["int", "i"])
    async def interval(self, ctx: Context, hours: Optional[int]):
        """
        change lookup interval (in hours)
        """

        if hours is None:
            await ctx.send(translations.f_reddit_interval(await run_in_thread(Settings.get, int, "reddit_interval", 4)))
            return

        if not 0 < hours < (1 << 31):
            raise CommandError(translations.invalid_interval)

        await run_in_thread(Settings.set, int, "reddit_interval", hours)
        await self.start_loop(hours)
        await ctx.send(translations.reddit_interval_set)
        await send_to_changelog(ctx.guild, translations.f_log_reddit_interval_set(hours))

    @reddit.command(name="limit", aliases=["lim"])
    async def limit(self, ctx: Context, limit: Optional[int]):
        """
        change limit of posts to be sent concurrently
        """

        if limit is None:
            await ctx.send(translations.f_reddit_limit(await run_in_thread(Settings.get, int, "reddit_limit", 4)))
            return

        if not 0 < limit < (1 << 31):
            raise CommandError(translations.invalid_limit)

        await run_in_thread(Settings.set, int, "reddit_limit", limit)
        await ctx.send(translations.reddit_limit_set)
        await send_to_changelog(ctx.guild, translations.f_log_reddit_limit_set(limit))

    @reddit.command(name="trigger", aliases=["t"])
    async def trigger(self, ctx: Context):
        """
        pull hot posts now and reset the timer
        """

        await self.start_loop(await run_in_thread(Settings.get, int, "reddit_interval", 4))
        await ctx.send(translations.done)

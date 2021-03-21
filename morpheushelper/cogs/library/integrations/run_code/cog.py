import re

from aiohttp import ClientError
from discord import Embed
from discord.ext import commands
from discord.ext.commands import CommandError, UserInputError
from sentry_sdk import capture_exception

from PyDrocsid.cog import Cog
from PyDrocsid.material_colors import MaterialColors
from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t
from PyDrocsid.util import send_long_embed
from .api import Emkc, EmkcAPIException
from cogs.library.contributor import Contributor

tg = t.g
t = t.run_code

N_CHARS = 1000

# fmt: off
LANGUAGES = [
    "awk", "bash", "brainfuck", "c", "cpp", "crystal", "csharp", "d", "dash", "deno", "elixir", "emacs", "go",
    "haskell", "java", "jelly", "julia", "kotlin", "lisp", "lua", "nasm", "nasm64", "nim", "node", "osabie",
    "paradoc", "perl", "php", "python2", "python3", "ruby", "rust", "swift", "typescript", "zig",
]
# fmt: on


def supported_languages_docs(f):
    f.__doc__ += f"\nSupported languages: {', '.join(f'`{lang}`' for lang in LANGUAGES)}"
    return f


class RunCodeCog(Cog):
    CONTRIBUTORS = [Contributor.Florian, Contributor.Defelo]
    PERMISSIONS = BasePermission

    @commands.command(usage=t.run_usage)
    @supported_languages_docs
    async def run(self, ctx, *, args: str):
        """
        run some code
        """

        if not (match := re.fullmatch(r"((```)?)([a-zA-Z\d]+)\n(.+?)\1", args, re.DOTALL)):
            raise UserInputError

        *_, language, source = match.groups()

        await ctx.trigger_typing()

        try:
            api_result: dict = await Emkc.run_code(language, source)
        except EmkcAPIException as e:
            if e.error == "Supplied language is not supported by Piston":
                raise CommandError(t.error_unsupported_language(language))

            capture_exception()
            raise CommandError(f"{t.error_run_code}: {e.error}")
        except ClientError:
            capture_exception()
            raise CommandError(t.error_run_code)

        output: str = api_result["output"]
        if len(output) > N_CHARS:
            newline = output.find("\n", N_CHARS, N_CHARS + 20)
            if newline == -1:
                newline = N_CHARS
            output = output[:newline] + "\n..."

        description = "```\n" + output.replace("`", "`\u200b") + "\n```"

        embed = Embed(title=t.run_output, color=MaterialColors.green, description=description)
        if api_result["stderr"] and not api_result["stdout"]:
            embed.colour = MaterialColors.error

        embed.set_footer(text=tg.requested_by(ctx.author, ctx.author.id), icon_url=ctx.author.avatar_url)

        await send_long_embed(ctx, embed)

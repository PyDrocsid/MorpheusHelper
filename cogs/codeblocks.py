from discord import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot


class CodeblocksCog(Cog, name="Codeblocks command"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="codeblocks", aliases=["cb"])
    async def codeblocks(self, ctx):
        desc = r"""\```sprache
<code>
\```

**Zum Beispiel**
\```py
print("Hello World")
\```
wird zu
```py
print("Hello World")
```
"""
        await ctx.send(embed=Embed(title="So benutzt man codeblocks", description=desc))

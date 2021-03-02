from PyDrocsid.translations import translations
from discord import Embed, File, Colour
from discord.ext import commands
from discord.ext.commands import Cog, Bot
import re
from PIL import ImageColor, Image
import io


class ColorPickerCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="colorpicker", aliases=["cp", "color"])
    async def colorpicker(self, ctx, color_code: str):
        if not (color_code_re := re.match(r'^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$', color_code)):
            embed: Embed = Embed(title=translations.f_error_parse_color(color_code),
                                 description=translations.error_parse_color_example)
            await ctx.send(embed=embed)  # TODO
            return
        rgb: tuple[int] = ImageColor.getcolor(color_code, "RGB")
        hsl: tuple[int] = ImageColor.getcolor(color_code, "HSV")
        img: Image = Image.new('RGB', (100, 100), rgb)
        with io.BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            embed: Embed = Embed(title='Colorpicker', color=Colour(int(color_code_re.group(1), 16)))
            embed.add_field(name='HEX', value=color_code)
            embed.add_field(name='RGB', value=str(rgb))
            embed.add_field(name='HSV', value=str(hsl))
            embed.set_image(url="attachment://color.png")
            await ctx.send(embed=embed, file=File(fp=image_binary, filename='color.png'))

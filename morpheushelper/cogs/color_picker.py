from PyDrocsid.translations import translations
from discord import Embed, File, Colour
from discord.ext import commands
from discord.ext.commands import Cog, Bot
import re
from PIL import ImageColor, Image
import io
import colorsys


class ColorPickerCog(Cog):
    RE_HEX = re.compile(r'^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$')
    RE_RGB = re.compile(r'^rgb\(([0-9]{1,3})\, ?([0-9]{1,3})\, ?([0-9]{1,3})\)$')
    RE_HSV = re.compile(r'^hsv\(([0-9]{1,3})\, ?([0-9]{1,3})\, ?([0-9]{1,3})\)$')
    RE_HSL = re.compile(r'^hsl\(([0-9]{1,3})\, ?([0-9]{1,3})\, ?([0-9]{1,3})\)$')

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="colorpicker", aliases=["cp", "color"])
    async def colorpicker(self, ctx, *, color: str):
        if color_re := self.RE_HEX.match(color):
            color_hex = color_re.group(1)
            rgb: tuple[int] = ImageColor.getcolor(color, "RGB")
            hsv: tuple[int] = ImageColor.getcolor(color, "HSV")
            # skipcq: PYL-E1120
            hsl = tuple(map(int, colorsys.rgb_to_hls(*rgb)))
        elif color_re := self.RE_RGB.match(color):
            rgb = (int(color_re.group(1)), int(color_re.group(2)), int(color_re.group(3)))
            color_hex = '%02x%02x%02x' % rgb
            hsv: tuple[int] = ImageColor.getcolor(f'#{color_hex}', "HSV")
            # skipcq: PYL-E1120
            hsl = tuple(map(int, colorsys.rgb_to_hls(*rgb)))
        elif color_re := self.RE_HSV.match(color):
            hsv: tuple[int] = (int(color_re.group(1)), int(color_re.group(2)), int(color_re.group(3)))
            # skipcq: PYL-E1120
            rgb = tuple(map(int,  colorsys.hsv_to_rgb(*hsv)))
            color_hex = '%02x%02x%02x' % rgb
            # skipcq: PYL-E1120
            hsl = tuple(map(int, colorsys.rgb_to_hls(*rgb)))
        elif color_re := self.RE_HSL.match(color):
            hsl: tuple[int] = (int(color_re.group(1)), int(color_re.group(2)), int(color_re.group(3)))
            # skipcq: PYL-E1120
            rgb = tuple(map(int,  colorsys.hls_to_rgb(*hsl)))
            # skipcq: PYL-E1120
            hsv = tuple(map(int, colorsys.rgb_to_hsv(*rgb)))
            color_hex = '%02x%02x%02x' % rgb
        else:
            embed: Embed = Embed(title=translations.f_error_parse_color(color),
                                 description=translations.error_parse_color_example)
            await ctx.send(embed=embed)
            return
        img: Image = Image.new('RGB', (100, 100), rgb)
        with io.BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            embed: Embed = Embed(title='Colorpicker', color=Colour(int(color_hex, 16)))
            embed.add_field(name='HEX', value=f'#{color_hex}')
            embed.add_field(name='RGB', value=f'rgb{rgb}')
            embed.add_field(name='HSV', value=f'hsv{hsv}')
            embed.add_field(name='HSL', value=f'hsl{hsl}')
            embed.set_image(url="attachment://color.png")
            await ctx.send(embed=embed, file=File(fp=image_binary, filename='color.png'))

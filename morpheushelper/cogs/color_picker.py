from PyDrocsid.translations import translations
from discord import Embed, File, Colour
from discord.ext import commands
from discord.ext.commands import Cog, Bot
import re
from PIL import ImageColor, Image
import io
import colorsys


class ColorPickerCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="colorpicker", aliases=["cp", "color"])
    async def colorpicker(self, ctx, *, color: str):
        if color_re := re.match(r'^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$', color):
            color_hex = color_re.group(1)
            rgb: tuple[int] = ImageColor.getcolor(color, "RGB")
            hsv: tuple[int] = ImageColor.getcolor(color, "HSV")
            hsl = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
            hsl = (int(hsl[0]), int(hsl[1]), int(hsl[2]))
        elif color_re := re.match(r'^rgb\(([0-9]{1,3})\, ?([0-9]{1,3})\, ?([0-9]{1,3})\)$', color):
            rgb = (int(color_re.group(1)), int(color_re.group(2)), int(color_re.group(3)))
            color_hex = '%02x%02x%02x' % rgb
            hsv: tuple[int] = ImageColor.getcolor('#' + color_hex, "HSV")
            hsl = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
            hsl = (int(hsl[0]), int(hsl[1]), int(hsl[2]))
        elif color_re := re.match(r'^hsv\(([0-9]{1,3})\, ?([0-9]{1,3})\, ?([0-9]{1,3})\)$', color):
            hsv: tuple[int] = (int(color_re.group(1)), int(color_re.group(2)), int(color_re.group(3)))
            rgb = colorsys.hsv_to_rgb(hsv[0], hsv[1], hsv[2])
            rgb = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
            color_hex = '%02x%02x%02x' % rgb
            hsl = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
            hsl = (int(hsl[0]), int(hsl[1]), int(hsl[2]))
        elif color_re := re.match(r'^hsl\(([0-9]{1,3})\, ?([0-9]{1,3})\, ?([0-9]{1,3})\)$', color):
            hsl: tuple[int] = (int(color_re.group(1)), int(color_re.group(2)), int(color_re.group(3)))
            rgb = colorsys.hls_to_rgb(hsl[0], hsl[1], hsl[2])
            rgb = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
            hsv = colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])
            hsv = (int(hsv[0]), int(hsv[1]), int(hsv[2]))
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
            embed.add_field(name='HEX', value='#' + color_hex)
            embed.add_field(name='RGB', value=f'rgb{rgb}')
            embed.add_field(name='HSV', value=f'hsv{hsv}')
            embed.add_field(name='HSL', value=f'hsl{hsl}')
            embed.set_image(url="attachment://color.png")
            await ctx.send(embed=embed, file=File(fp=image_binary, filename='color.png'))

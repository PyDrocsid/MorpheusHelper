class NestedInt(int):
    _values = {}

    def __new__(cls, x, values):
        obj = super(NestedInt, cls).__new__(cls, x)
        obj._values = values
        return obj

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return self._values.__iter__()

    def items(self):
        return self._values.items()


class MaterialColors:
    red = NestedInt(
        0xF44336,
        {
            50: 0xFFEBEE,
            100: 0xFFCDD2,
            200: 0xEF9A9A,
            300: 0xE57373,
            400: 0xEF5350,
            500: 0xF44336,
            600: 0xE53935,
            700: 0xD32F2F,
            800: 0xC62828,
            900: 0xB71C1C,
            "a100": 0xFF8A80,
            "a200": 0xFF5252,
            "a400": 0xFF1744,
            "a700": 0xD50000,
        },
    )
    pink = NestedInt(
        0xE91E63,
        {
            50: 0xFCE4EC,
            100: 0xF8BBD0,
            200: 0xF48FB1,
            300: 0xF06292,
            400: 0xEC407A,
            500: 0xE91E63,
            600: 0xD81B60,
            700: 0xC2185B,
            800: 0xAD1457,
            900: 0x880E4F,
            "a100": 0xFF80AB,
            "a200": 0xFF4081,
            "a400": 0xF50057,
            "a700": 0xC51162,
        },
    )
    purple = NestedInt(
        0x9C27B0,
        {
            50: 0xF3E5F5,
            100: 0xE1BEE7,
            200: 0xCE93D8,
            300: 0xBA68C8,
            400: 0xAB47BC,
            500: 0x9C27B0,
            600: 0x8E24AA,
            700: 0x7B1FA2,
            800: 0x6A1B9A,
            900: 0x4A148C,
            "a100": 0xEA80FC,
            "a200": 0xE040FB,
            "a400": 0xD500F9,
            "a700": 0xAA00FF,
        },
    )
    deeppurple = NestedInt(
        0x673AB7,
        {
            50: 0xEDE7F6,
            100: 0xD1C4E9,
            200: 0xB39DDB,
            300: 0x9575CD,
            400: 0x7E57C2,
            500: 0x673AB7,
            600: 0x5E35B1,
            700: 0x512DA8,
            800: 0x4527A0,
            900: 0x311B92,
            "a100": 0xB388FF,
            "a200": 0x7C4DFF,
            "a400": 0x651FFF,
            "a700": 0x6200EA,
        },
    )
    indigo = NestedInt(
        0x3F51B5,
        {
            50: 0xE8EAF6,
            100: 0xC5CAE9,
            200: 0x9FA8DA,
            300: 0x7986CB,
            400: 0x5C6BC0,
            500: 0x3F51B5,
            600: 0x3949AB,
            700: 0x303F9F,
            800: 0x283593,
            900: 0x1A237E,
            "a100": 0x8C9EFF,
            "a200": 0x536DFE,
            "a400": 0x3D5AFE,
            "a700": 0x304FFE,
        },
    )
    blue = NestedInt(
        0x2196F3,
        {
            50: 0xE3F2FD,
            100: 0xBBDEFB,
            200: 0x90CAF9,
            300: 0x64B5F6,
            400: 0x42A5F5,
            500: 0x2196F3,
            600: 0x1E88E5,
            700: 0x1976D2,
            800: 0x1565C0,
            900: 0x0D47A1,
            "a100": 0x82B1FF,
            "a200": 0x448AFF,
            "a400": 0x2979FF,
            "a700": 0x2962FF,
        },
    )
    lightblue = NestedInt(
        0x03A9F4,
        {
            50: 0xE1F5FE,
            100: 0xB3E5FC,
            200: 0x81D4FA,
            300: 0x4FC3F7,
            400: 0x29B6F6,
            500: 0x03A9F4,
            600: 0x039BE5,
            700: 0x0288D1,
            800: 0x0277BD,
            900: 0x01579B,
            "a100": 0x80D8FF,
            "a200": 0x40C4FF,
            "a400": 0x00B0FF,
            "a700": 0x0091EA,
        },
    )
    cyan = NestedInt(
        0x00BCD4,
        {
            50: 0xE0F7FA,
            100: 0xB2EBF2,
            200: 0x80DEEA,
            300: 0x4DD0E1,
            400: 0x26C6DA,
            500: 0x00BCD4,
            600: 0x00ACC1,
            700: 0x0097A7,
            800: 0x00838F,
            900: 0x006064,
            "a100": 0x84FFFF,
            "a200": 0x18FFFF,
            "a400": 0x00E5FF,
            "a700": 0x00B8D4,
        },
    )
    teal = NestedInt(
        0x009688,
        {
            50: 0xE0F2F1,
            100: 0xB2DFDB,
            200: 0x80CBC4,
            300: 0x4DB6AC,
            400: 0x26A69A,
            500: 0x009688,
            600: 0x00897B,
            700: 0x00796B,
            800: 0x00695C,
            900: 0x004D40,
            "a100": 0xA7FFEB,
            "a200": 0x64FFDA,
            "a400": 0x1DE9B6,
            "a700": 0x00BFA5,
        },
    )
    green = NestedInt(
        0x4CAF50,
        {
            50: 0xE8F5E9,
            100: 0xC8E6C9,
            200: 0xA5D6A7,
            300: 0x81C784,
            400: 0x66BB6A,
            500: 0x4CAF50,
            600: 0x43A047,
            700: 0x388E3C,
            800: 0x2E7D32,
            900: 0x1B5E20,
            "a100": 0xB9F6CA,
            "a200": 0x69F0AE,
            "a400": 0x00E676,
            "a700": 0x00C853,
        },
    )
    lightgreen = NestedInt(
        0x8BC34A,
        {
            50: 0xF1F8E9,
            100: 0xDCEDC8,
            200: 0xC5E1A5,
            300: 0xAED581,
            400: 0x9CCC65,
            500: 0x8BC34A,
            600: 0x7CB342,
            700: 0x689F38,
            800: 0x558B2F,
            900: 0x33691E,
            "a100": 0xCCFF90,
            "a200": 0xB2FF59,
            "a400": 0x76FF03,
            "a700": 0x64DD17,
        },
    )
    lime = NestedInt(
        0xCDDC39,
        {
            50: 0xF9FBE7,
            100: 0xF0F4C3,
            200: 0xE6EE9C,
            300: 0xDCE775,
            400: 0xD4E157,
            500: 0xCDDC39,
            600: 0xC0CA33,
            700: 0xAFB42B,
            800: 0x9E9D24,
            900: 0x827717,
            "a100": 0xF4FF81,
            "a200": 0xEEFF41,
            "a400": 0xC6FF00,
            "a700": 0xAEEA00,
        },
    )
    yellow = NestedInt(
        0xFFEB3B,
        {
            50: 0xFFFDE7,
            100: 0xFFF9C4,
            200: 0xFFF59D,
            300: 0xFFF176,
            400: 0xFFEE58,
            500: 0xFFEB3B,
            600: 0xFDD835,
            700: 0xFBC02D,
            800: 0xF9A825,
            900: 0xF57F17,
            "a100": 0xFFFF8D,
            "a200": 0xFFFF00,
            "a400": 0xFFEA00,
            "a700": 0xFFD600,
        },
    )
    amber = NestedInt(
        0xFFC107,
        {
            50: 0xFFF8E1,
            100: 0xFFECB3,
            200: 0xFFE082,
            300: 0xFFD54F,
            400: 0xFFCA28,
            500: 0xFFC107,
            600: 0xFFB300,
            700: 0xFFA000,
            800: 0xFF8F00,
            900: 0xFF6F00,
            "a100": 0xFFE57F,
            "a200": 0xFFD740,
            "a400": 0xFFC400,
            "a700": 0xFFAB00,
        },
    )
    orange = NestedInt(
        0xFF9800,
        {
            50: 0xFFF3E0,
            100: 0xFFE0B2,
            200: 0xFFCC80,
            300: 0xFFB74D,
            400: 0xFFA726,
            500: 0xFF9800,
            600: 0xFB8C00,
            700: 0xF57C00,
            800: 0xEF6C00,
            900: 0xE65100,
            "a100": 0xFFD180,
            "a200": 0xFFAB40,
            "a400": 0xFF9100,
            "a700": 0xFF6D00,
        },
    )
    deeporange = NestedInt(
        0xFF5722,
        {
            50: 0xFBE9E7,
            100: 0xFFCCBC,
            200: 0xFFAB91,
            300: 0xFF8A65,
            400: 0xFF7043,
            500: 0xFF5722,
            600: 0xF4511E,
            700: 0xE64A19,
            800: 0xD84315,
            900: 0xBF360C,
            "a100": 0xFF9E80,
            "a200": 0xFF6E40,
            "a400": 0xFF3D00,
            "a700": 0xDD2C00,
        },
    )
    brown = NestedInt(
        0x795548,
        {
            50: 0xEFEBE9,
            100: 0xD7CCC8,
            200: 0xBCAAA4,
            300: 0xA1887F,
            400: 0x8D6E63,
            500: 0x795548,
            600: 0x6D4C41,
            700: 0x5D4037,
            800: 0x4E342E,
            900: 0x3E2723,
        },
    )
    grey = NestedInt(
        0x9E9E9E,
        {
            50: 0xFAFAFA,
            100: 0xF5F5F5,
            200: 0xEEEEEE,
            300: 0xE0E0E0,
            400: 0xBDBDBD,
            500: 0x9E9E9E,
            600: 0x757575,
            700: 0x616161,
            800: 0x424242,
            900: 0x212121,
        },
    )
    bluegrey = NestedInt(
        0x607D8B,
        {
            50: 0xECEFF1,
            100: 0xCFD8DC,
            200: 0xB0BEC5,
            300: 0x90A4AE,
            400: 0x78909C,
            500: 0x607D8B,
            600: 0x546E7A,
            700: 0x455A64,
            800: 0x37474F,
            900: 0x263238,
        },
    )

    default = teal
    error = red
    warning = yellow[700]

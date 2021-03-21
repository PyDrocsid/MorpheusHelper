import hashlib
import http
import string
from urllib.parse import urlencode

import requests


def md5(data):
    return hashlib.md5(data[7:33]).hexdigest().encode()  # noqa: S303


class CleverBot:
    URL = "https://www.cleverbot.com/webservicemin?uc=UseOfficialCleverbotAPI&"

    def __init__(self):
        self.history = []
        self.result = None
        self.session = requests.Session()
        self.ns = 1
        self.session.get("https://www.cleverbot.com/")
        self.set_cookie("_cbsid", "-1")
        self.cnt = 0

    def say(self, msg):
        self.cnt += 1
        msg = "".join([[c, " "][c in string.whitespace] for c in msg if 32 <= ord(c) < 256])
        if self.ns == 1:
            d = urlencode(
                {
                    "stimulus": msg,
                    "cb_settings_language": "en",
                    "cb_settings_scripting": "no",
                    "islearning": "1",
                    "icognoid": "wsf",
                },
            ).encode()
            d += b"&icognocheck="
            d += md5(d)
            result = self.session.post(self.URL, data=d)
            out = "".join([c for c in result.content.split(b"\r")[0].decode() if ord(c) < 256])
            result = result.text.split("\r")

            self.set_cookie("CBALT", "1~" + out)

            self.session.get(
                self.URL,
                params={
                    "out": "",
                    "in": msg,
                    "bot": "c",
                    "cbsid": result[1],
                    "xai": "MCA",
                    "ns": 1,
                    "al": "",
                    "dl": "",
                    "flag": "",
                    "user": "",
                    "mode": 1,
                    "alt": 0,
                    "reac": "",
                    "emo": "",
                    "sou": "website",
                    "xed": "",
                },
            )

            self.set_cookie("CBSID", result[1])
            self.set_cookie("CBSTATE", "&&0&&0&1&" + msg + "&" + result[0])

            self.history = [out, msg]
            self.result = result
        else:
            d = urlencode(
                {
                    "stimulus": msg,
                    **{f"vText{i + 2}": h for i, h in enumerate(self.history)},
                    "cb_settings_language": "en",
                    "cb_settings_scripting": "no",
                    "islearning": "1",
                    "icognoid": "wsf",
                },
            ).encode()
            d += b"&icognocheck="
            d += md5(d)
            result = self.session.post(
                self.URL,
                params={
                    "out": self.result[0],
                    "in": msg,
                    "bot": "c",
                    "cbsid": self.result[1],
                    "xai": "MCA," + self.result[2],
                    "ns": str(self.ns),
                    "al": "",
                    "dl": "en",
                    "flag": "",
                    "user": "",
                    "mode": 1,
                    "alt": 0,
                    "reac": "",
                    "emo": "",
                    "sou": "website",
                    "xed": "",
                },
                data=d,
            )
            out = "".join([c for c in result.content.split(b"\r")[0].decode() if ord(c) < 256])
            result = result.text.split("\r")

            self.history = [out, msg] + self.history
            self.result = result

            self.set_cookie("CBALT", "1~" + out)

            cbstate = f"&&0&&0&{self.ns}&"
            cbstate += "&".join([self.history[i] for i in range(len(self.history) - 1, -1, -1)])
            self.set_cookie("CBSTATE", cbstate)

        self.ns += 1
        return out

    def set_cookie(self, name, value):
        # noinspection PyProtectedMember,PyUnresolvedReferences
        # skipcq: PYL-W0212
        self.session.cookies._cookies["www.cleverbot.com"]["/"][name] = http.cookiejar.Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain="www.cleverbot.com",
            domain_specified=False,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )

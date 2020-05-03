import requests
import hashlib
import http
import string
import json


class CleverBot:
    URL = "https://www.cleverbot.com/webservicemin?uc=UseOfficialCleverbotAPI&"
    encode = lambda self, x: "".join([a if a in string.printable[:62] else "%" + hex(ord(a))[2:] for a in x])
    md5 = lambda self, d: hashlib.md5(d[7:33]).hexdigest().encode()

    def __init__(self, data=None):
        self.history = []
        self.result = None
        self.session = requests.Session()
        self.ns = 1
        self.session.get("https://www.cleverbot.com/")
        self.set_cookie("_cbsid", "-1")
        if data is not None:
            self.history = data["history"]
            self.result = data["result"]
            self.ns = data["ns"]
            for name, value in data["cookies"].items():
                self.set_cookie(name, value)

    def dumps(self):
        cookies = {name: value.value for name, value in self.session.cookies._cookies["www.cleverbot.com"]["/"].items()}
        out = {"history": self.history, "result": self.result, "ns": self.ns, "cookies": cookies}
        return out

    def dump(self, file):
        json.dump(self.dumps(), open(file, "w"))

    @staticmethod
    def load(file):
        return CleverBot(json.load(open(file)))

    def say(self, msg):
        out = None
        msg = "".join([c for c in msg if ord(c) < 256])
        if self.ns == 1:
            inp = self.encode(msg)
            d = b"stimulus=" + inp.encode()
            d += b"&cb_settings_language=en"
            d += b"&cb_settings_scripting=no&islearning=1&icognoid=wsf&icognocheck="
            d += self.md5(d)
            result = self.session.post(self.URL, data=d)  # .text.split("\r")
            out = "".join([c for c in result.content.split(b"\r")[0].decode() if ord(c) < 256])
            result = result.text.split("\r")

            self.set_cookie("CBALT", "1~" + out)

            self.session.get(
                self.URL
                + "out=&in="
                + inp
                + "&bot=c&cbsid="
                + result[1]
                + "&xai=MCA&ns=1&al=&dl=&flag=&user=&mode=1&alt=0&reac=&emo=&sou=website&xed=&"
            )

            self.set_cookie("CBSID", result[1])
            self.set_cookie("CBSTATE", "&&0&&0&1&" + msg + "&" + result[0])

            self.history = [out, msg]
            self.result = result
        else:
            inp = self.encode(msg)
            d = b"stimulus=" + inp.encode()
            for i in range(len(self.history)):
                d += ("&vText%s=%s" % (i + 2, self.encode(self.history[i]))).encode()
            d += b"&cb_settings_language=en"
            d += b"&cb_settings_scripting=no&islearning=1&icognoid=wsf&icognocheck="
            d += self.md5(d)
            result = self.session.post(
                self.URL
                + "out="
                + self.encode(self.result[0])
                + "&in="
                + inp
                + "&bot=c&cbsid="
                + self.result[1]
                + "&xai=MCA,"
                + self.result[2]
                + "&ns="
                + str(self.ns)
                + "&al=&dl=en&flag=&user=&mode=1&alt=0&reac=&emo=&sou=website&xed=&",
                data=d,
            )  # .text.split("\r")
            out = "".join([c for c in result.content.split(b"\r")[0].decode() if ord(c) < 256])
            result = result.text.split("\r")

            self.history = [out, msg] + self.history
            self.result = result

            self.set_cookie("CBALT", "1~" + out)
            self.set_cookie(
                "CBSTATE",
                "&&0&&0&"
                + str(self.ns)
                + "&"
                + "&".join([self.history[i] for i in range(len(self.history) - 1, -1, -1)]),
            )
        self.ns += 1
        return out

    def set_cookie(self, name, value):
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

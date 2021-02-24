from subprocess import getoutput  # skipcq: BAN-B404

from requests import get

VERSION = getoutput("cat VERSION 2>/dev/null || git describe").lstrip("v")
MORPHEUS_ICON = "https://cdn.discordapp.com/avatars/686299664726622258/cb99c816286bdd1d988ec16d8ae85e15.png"
CONTRIBUTORS = [
    212866839083089921,  # @TNT2k#7587
    339062431131369472,  # @wolflu#5506
    306774624090456075,  # @ce_phox#1259
    137906177487929344,  # @Scriptim#3540
    302365095688798209,  # @MaxiHuHe04#8905
    541341790176018432,  # @Florian#1234
    330148908531580928,  # @AdriBloober#1260
]
GITHUB_LINK = "https://github.com/Defelo/MorpheusHelper"
AVATAR_URL = "https://github.com/Defelo.png"
GITHUB_DESCRIPTION = get("https://api.github.com/repos/Defelo/MorpheusHelper").json()["description"]

from subprocess import getoutput  # skipcq: BAN-B404

VERSION = getoutput("cat VERSION 2>/dev/null || git describe").lstrip("v")
MORPHEUS_ICON = "https://cdn.discordapp.com/avatars/686299664726622258/cb99c816286bdd1d988ec16d8ae85e15.png"
CONTRIBUTORS = [
    212866839083089921,
    137906177487929344,
    302365095688798209,
    306774624090456075,
    541341790176018432,
    330148908531580928,
]
GITHUB_LINK = "https://github.com/Defelo/MorpheusHelper"

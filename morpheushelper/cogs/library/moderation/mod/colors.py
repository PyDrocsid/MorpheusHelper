from PyDrocsid.material_colors import MaterialColors


class Colors(MaterialColors):
    ModTools = MaterialColors.blue["a700"]

    report = MaterialColors.yellow[800]
    warn = MaterialColors.yellow["a200"]
    mute = MaterialColors.yellow[600]
    unmute = MaterialColors.green["a700"]
    kick = MaterialColors.orange[700]
    ban = MaterialColors.red[500]
    unban = MaterialColors.green["a700"]

    stats = MaterialColors.green
    userlog = MaterialColors.green["a400"]

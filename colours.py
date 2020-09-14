from PyDrocsid.material_colours import MaterialColours, NestedInt


class Colours(MaterialColours):
    # General
    default = MaterialColours.teal
    error = MaterialColours.red

    # Cogs
    AllowedInvites = MaterialColours.lightgreen["a700"]
    AutoMod = MaterialColours.blue["a700"]
    CleverBot = 0x8EBBF6  # clever bot color
    CodeBlocks = MaterialColours.grey[900]
    Logging = NestedInt(
        MaterialColours.blue["a700"], {"edit": MaterialColours.yellow["a200"], "delete": MaterialColours.yellow["a200"]}
    )
    MediaOnly = MaterialColours.yellow["a200"]
    MetaQuestions = MaterialColours.purple["a400"]
    ModTools = MaterialColours.blue["a700"]
    News = MaterialColours.orange
    Permissions = MaterialColours.blue["a700"]
    Polls = MaterialColours.orange[800]
    ReactionPin = MaterialColours.blue["a700"]
    ReactionRole = MaterialColours.blue["a700"]
    Reddit = 0xFF4500  # Reddit color
    RuleCommands = MaterialColours.blue["a700"]
    BeTheProfessional = MaterialColours.yellow["a200"]
    ServerInformation = MaterialColours.indigo
    Verification = MaterialColours.green["a100"]
    Voice = NestedInt(
        MaterialColours.blue["a700"],
        {"public": MaterialColours.lightgreen["a700"], "private": MaterialColours.blue["a700"]},
    )

    # Commands
    changelog = MaterialColours.teal
    github = MaterialColours.grey[900]
    info = MaterialColours.indigo
    ping = MaterialColours.lightgreen["a400"]
    prefix = MaterialColours.indigo
    stats = MaterialColours.green
    userlog = MaterialColours.green["a400"]
    version = MaterialColours.indigo

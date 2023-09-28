# Define a dictionary to store key information
key_info = {
    "<MF C major": {
        "chord_notes": "C D E F G A B",
        "relative_minor": "A minor",
        "parallel_minor": "C minor"
    },
    "<MF D major": {
        "chord_notes": "D E F# G A B C#",
        "relative_minor": "B minor",
        "parallel_minor": "D minor"
    },
    "<MF E major": {
        "chord_notes": "E F# G# A B C# D#",
        "relative_minor": "C# minor",
        "parallel_minor": "E minor"
    },
    "<MF F major": {
        "chord_notes": "F G A Bb C D E",
        "relative_minor": "D minor",
        "parallel_minor": "F minor"
    },
    "<MF G major": {
        "chord_notes": "G A B C D E F#",
        "relative_minor": "E minor",
        "parallel_minor": "G minor"
    },
    "<MF A major": {
        "chord_notes": "A B C# D E F# G#",
        "relative_minor": "F# minor",
        "parallel_minor": "A minor"
    },
    "<MF B major": {
        "chord_notes": "B C# D# E F# G# A#",
        "relative_minor": "G# minor",
        "parallel_minor": "B minor"
    },
    "<MF C# major": {
        "chord_notes": "C# D# E# F# G# A# B#",
        "relative_minor": "A# minor",
        "parallel_minor": "C# minor"
    },
    "<MF Db major": {
        "chord_notes": "Db Eb F Gb Ab Bb C",
        "relative_minor": "Bb minor",
        "parallel_minor": "C# minor"
    },
    "<MF D# major": {
        "chord_notes": "D# E# F## G# A# B# C##",
        "relative_minor": "B# minor",
        "parallel_minor": "D# minor"
    },
    "<MF Eb major": {
        "chord_notes": "Eb F G Ab Bb C D",
        "relative_minor": "C minor",
        "parallel_minor": "Eb minor"
    },
    "<MF F# major": {
        "chord_notes": "F# G# A# B C# D# E#",
        "relative_minor": "D# minor",
        "parallel_minor": "F# minor"
    },
    "<MF Gb major": {
        "chord_notes": "Gb Ab Bb Cb Db Eb F",
        "relative_minor": "Eb minor",
        "parallel_minor": "Gb minor"
    },
    "<MF G# major": {
        "chord_notes": "G# A# B# C# D# E# F##",
        "relative_minor": "F## minor",
        "parallel_minor": "G# minor"
    },
    "<MF Ab major": {
        "chord_notes": "Ab Bb C Db Eb F G",
        "relative_minor": "F minor",
        "parallel_minor": "Ab minor"
    },
    "<MF A# major": {
        "chord_notes": "A# B# C## D# E# F## G##",
        "relative_minor": "C## minor",
        "parallel_minor": "A# minor"
    },
    "<MF Bb major": {
        "chord_notes": "Bb C D Eb F G A",
        "relative_minor": "G minor",
        "parallel_minor": "Bb minor"
    },
    "<MF B# major": {
        "chord_notes": "B# C## D## E# F## G## A##",
        "relative_minor": "G## minor",
        "parallel_minor": "B# minor"
    },
    "<MF Cb major": {
        "chord_notes": "Cb Db Eb Fb Gb Ab Bb",
        "relative_minor": "Ab minor",
        "parallel_minor": "Cb minor"
    }
}

content = message.content
for command, info in key_info.items():
    if content.startswith(command):
        if "chord_notes" in info:
            await send(info["chord_notes"])
        elif "relative_minor" in info:
            await send(
                f"`{info['chord_notes']}`\n\nThe relative minor is {info['relative_minor']}.\nThe parallel minor is {info['parallel_minor']}.")

# Triads
start = message.content.startswith
degree = "\u00b0"
# Majors
if start("<MF chords C major"):
    guild = client.get_guild(732355624259813531)
    myEmbed = discord.Embed(color=0x7e016f)
    myEmbed.set_author(name="C Major Chords", icon_url=guild.icon_url)
    myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
    myEmbed.add_field(name="Chords", value="`C major\nD minor\nE minor\nF major\nG major\nA minor\nB dim`", inline=True)
    myEmbed.add_field(name="Notes",
                      value="`C E G (B)\nD F A (C)\nE G B (D)\nF A C (E)\nG B D (F)\nA C E (G)\nB D F (A)`",
                      inline=True)
    await send(embed=myEmbed)
if start("<MF chords D major"):
    guild = client.get_guild(732355624259813531)
    myEmbed = discord.Embed(color=0x7e016f)
    myEmbed.set_author(name="D Major Chords", icon_url=guild.icon_url)
    myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
    myEmbed.add_field(name="Chords",
                      value=f"`D major\nE minor\nF{sharp} minor\nG major\nA major\nB minor\nC{sharp} dim`", inline=True)
    myEmbed.add_field(name="Notes",
                      value=f"`D F{sharp} A (C{sharp})\nE G B (D)\nF{sharp} A C{sharp} (E)\nG B D (F{sharp})\nA C{sharp} E (G)\nB D F (A)\nC{sharp} E G (B)`",
                      inline=True)
    await send(embed=myEmbed)
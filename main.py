import discord
import json
import asyncio
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True

client = commands.Bot(command_prefix="<", intents=intents)
client.remove_command("help")


# Bot is online
@client.event
async def on_ready():
    general_chat = client.get_channel(749443325530079314)

    await general_chat.send("Music Feedback is online.")


@client.event
async def on_member_join(member):
    with open("MF Points.json", "r") as f:
        users = json.load(f)

        await update_data(users, member)

    with open("MF Points.json", "w") as f:
        json.dump(users, f)


@client.event
async def on_message(message):
    with open("MF Points.json", "r") as f:
        users = json.load(f)

        if message.author.id == client.user.id:
            return
        else:

            await update_data(users, message.author)
            await add_points_to_json(users, message.author, message)
            await use_points_from_json(users, message.author, message)
            await balance(users, message.author, message)
            await leaderboard(users, message.author, message)
            await top_photo(users, message.author, message)

    with open("MF Points.json", "w") as f:
        json.dump(users, f, indent=4)

    # MF event submissions
    if message.content.startswith("<MF submit"):
        if message.attachments:
            if message.channel.id == 736318707260719155 or message.channel.id == 732355624733638748 or message.channel.id == 772312046569127947:
                file = await message.attachments[0].to_file()
                await message.delete()

                guild = client.get_guild(732355624259813531)
                myEmbed = discord.Embed(color=0x7e016f)
                myEmbed.add_field(name=":ballot_box_with_check:  Success!", value="Your submission has been received.",
                                  inline=False)
                await message.channel.send(embed=myEmbed)
                channel = client.get_channel(811399805406019595)
                await channel.send(
                    f"-----------\n**Sent from:** <#{message.channel.id}>\n**Submitted by:** <@!{message.author.id}>\n {message.content}",
                    file=file)

        elif message.channel.id == 736318707260719155 or message.channel.id == 732355624733638748 or message.channel.id == 772312046569127947:
            await message.delete()

            guild = client.get_guild(732355624259813531)
            myEmbed = discord.Embed(color=0x7e016f)
            myEmbed.add_field(name=":ballot_box_with_check:  Success!", value="Your submission has been received.",
                              inline=False)
            await message.channel.send(embed=myEmbed)
            channel = client.get_channel(811399805406019595)
            await channel.send(
                f"-----------\n**Sent from:** <#{message.channel.id}>\n**Submitted by:** <@!{message.author.id}>\n {message.content}")  # prints out the message

    # Keys
    sharp = "#"
    send = message.channel.send
    # Majors
    if message.content.startswith("<MF C major"):
        await send("`C D E F G A B`\n\nThe relative minor is A minor. \nThe parallel minor is C minor.")
    if message.content.startswith("<MF D major"):
        await send(
            "`D E F" + sharp + " G A B C" + sharp + "`\n\nThe relative minor is B minor. \nThe parallel minor is D minor.")
    if message.content.startswith("<MF E major"):
        await send(
            "`E F" + sharp + " G" + sharp + " A B C" + sharp + " D" + sharp + "`\n\nThe relative minor is C" + sharp + " minor. \nThe parallel minor is E minor.")
    if message.content.startswith("<MF F major"):
        await send("`F G A Bb C D E`\n\nThe relative minor is D minor. \nThe parallel minor is F minor.")
    if message.content.startswith("<MF G major"):
        await send("`G A B C D E F" + sharp + "`\n\nThe relative minor is E minor. \nThe parallel minor is G minor.")
    if message.content.startswith("<MF A major"):
        await send(
            "`A B C" + sharp + " D E F" + sharp + " G" + sharp + "`\n\nThe relative minor is F" + sharp + " minor. \nThe parallel minor is A minor.")
    if message.content.startswith("<MF B major"):
        await send(
            "`B C" + sharp + " D" + sharp + " E F" + sharp + " G" + sharp + " A" + sharp + "`\n\nThe relative minor is G" + sharp + " minor. \nThe parallel minor is B minor.")
    # Sharp/Flat majors
    if message.content.startswith("<MF C# major"):
        await send(
            "`C" + sharp + " D" + sharp + " E" + sharp + " F" + sharp + " G" + sharp + " A" + sharp + " B" + sharp + "`\n\nThe relative minor is A" + sharp + " minor. \nThe parallel minor is C" + sharp + " minor.")
    if message.content.startswith("<MF Db major"):
        await send(
            "`Db Eb F Gb Ab Bb C`\n\nThe relative minor is Bb minor. \nThe parallel minor is C" + sharp + " minor.")
    if message.content.startswith("<MF D# major"):
        await send("Most commonly notated as Eb major.")
    if message.content.startswith("<MF Eb major"):
        await send("`Eb F G Ab Bb C D`\n\nThe relative minor is C minor. \nThe parallel minor is Eb minor.")
    if message.content.startswith("<MF F# major"):
        await send(
            "`F" + sharp + " G" + sharp + " A" + sharp + " B C" + sharp + " D" + sharp + " E" + sharp + "`\n\nThe relative minor is D" + sharp + " minor. \nThe parallel minor is F" + sharp + " minor.")
    if message.content.startswith("<MF Gb major"):
        await send("`Gb Ab Bb Cb Db Eb F`\n\nThe relative minor is Eb minor. \nThe parallel minor is Gb minor.")
    if message.content.startswith("<MF G# major"):
        await send("Most commonly notated as Ab major.")
    if message.content.startswith("<MF Ab major"):
        await send(
            "`Ab Bb C Db Eb F G`\n\nThe relative minor is F minor. \nThe parallel minor is Ab minor (more often G" + sharp + " minor).")
    if message.content.startswith("<MF A# major"):
        await send("Most commonly notated as Bb major.")
    if message.content.startswith("<MF Bb major"):
        await send("`Bb C D Eb F G A`\n\nThe relative minor is G minor. \nThe parallel minor is Bb minor.")
    if message.content.startswith("<MF B# major"):
        await send("Most commonly notated as Cb major.")
    if message.content.startswith("<MF Cb major"):
        await send(
            "`Cb Db Eb Fb Gb Ab Bb`\n\nThe relative minor is Ab minor. \nThe parallel minor is Cb minor (more often as B minor).")
    # Minors
    if message.content.startswith("<MF C minor"):
        await send("`C D Eb F G Ab Bb`\n\nThe relative major is Eb major. \nThe parallel major is C major.")
    if message.content.startswith("<MF D minor"):
        await send("`D E F G A Bb C`\n\nThe relative major is F major. \nThe parallel major is D major.")
    if message.content.startswith("<MF E minor"):
        await send("`E F" + sharp + " G A B C D`\n\nThe relative major is G major. \nThe parallel major is E major.")
    if message.content.startswith("<MF F minor"):
        await send("`F G Ab Bb C Db Eb`\n\nThe relative major is Ab major. \nThe parallel major is F major.")
    if message.content.startswith("<MF G minor"):
        await send("`G A Bb C D Eb F`\n\nThe relative major is Bb major. \nThe parallel major is G major.")
    if message.content.startswith("<MF A minor"):
        await send("`A B C D E F G`\n\nThe relative major is C major. \nThe parallel major is A major.")
    if message.content.startswith("<MF B minor"):
        await send(
            "`B C" + sharp + " D E F" + sharp + " G A`\n\nThe relative major is D major. \nThe parallel major is B major.")
    # Sharp/Flat minors
    if message.content.startswith("<MF C# minor"):
        await send(
            "`C" + sharp + " D" + sharp + " E F" + sharp + " G" + sharp + " A B`\n\nThe relative major is E major. \nThe parallel major is C" + sharp + " (more often as Db major).")
    if message.content.startswith("<MF Db minor"):
        await send("Most commonly notated as C# minor.")
    if message.content.startswith("<MF D# minor"):
        await send(
            "`D" + sharp + " E" + sharp + " F" + sharp + " G" + sharp + " A" + sharp + " B C" + sharp + "`\n\nThe relative major is F" + sharp + " major. \nThe parallel major is D" + sharp + " major (most often as Eb major).")
    if message.content.startswith("<MF Eb minor"):
        await send("`Eb F Gb Ab Bb Cb Db`\n\nThe relative major is Gb major. \nThe parallel major is Eb major.")
    if message.content.startswith("<MF F# minor"):
        await send(
            "`F" + sharp + " G" + sharp + " A B C" + sharp + " D E`\n\nThe relative major is A major. \nThe parallel major is F" + sharp + " major.")
    if message.content.startswith("<MF Gb minor"):
        await send("Most commonly notated as F" + sharp + " minor.")
    if message.content.startswith("<MF G# minor"):
        await send(
            "`G" + sharp + " A" + sharp + " B C" + sharp + " D" + sharp + " E F" + sharp + "`\n\nThe relative major is B major. \nThe parallel major is G" + sharp + " major (more often as Ab major).")
    if message.content.startswith("<MF Ab minor"):
        await send("`Ab Bb Cb Db Eb Fb Gb`\n\nThe relative major is Cb major. \nThe parallel major is Ab major.")
    if message.content.startswith("<MF A# minor"):
        await send(
            "`A" + sharp + " B" + sharp + " C" + sharp + " D" + sharp + " E" + sharp + " F" + sharp + " G" + sharp + "`\n\nThe relative major is C" + sharp + " major. \nThe parallel major is A" + sharp + " major (more often as Bb major).")
    if message.content.startswith("<MF Bb minor"):
        await send("`Bb C Db Eb F Gb Ab`\n\nThe relative major is Db major. \nThe parallel major is Bb major.")
    if message.content.startswith("<MF B# minor"):
        await send("Theoretical key.")
    if message.content.startswith("<MF Cb minor"):
        await send("Theoretical key.")

    # Triads
    start = message.content.startswith
    degree = "\u00b0"
    # Majors
    if start("<MF chords C major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="C Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value="`C major\nD minor\nE minor\nF major\nG major\nA minor\nB dim`",
                          inline=True)
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
                          value=f"`D major\nE minor\nF{sharp} minor\nG major\nA major\nB minor\nC{sharp} dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`D F{sharp} A (C{sharp})\nE G B (D)\nF{sharp} A C{sharp} (E)\nG B D (F{sharp})\nA C{sharp} E (G)\nB D F (A)\nC{sharp} E G (B)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords E major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="E Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`E major\nF{sharp} minor\nG{sharp} minor\nA major\nB major\nC{sharp} minor\nD{sharp} dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`E G{sharp} B (D{sharp})\nF{sharp} B D{sharp} (E)\nG{sharp} B D{sharp} (F{sharp})\nA C{sharp} E (G{sharp})\nB D{sharp} F{sharp} (A)\nC{sharp} E G{sharp} (B)\nD{sharp} F{sharp} A (C{sharp})`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords F major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="F Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value="`F major\nG minor\nA minor\nBb major\nC major\nD minor\nE dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`F A C (E)\nG Bb D (F)\nA C E (G)\nBb D F A\nC E G (Bb)\nD F A (C)\nE G Bb (D)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords G major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="G Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value=f"`G major\nA minor\nB minor\nC major\nD major\nE minor\nF{sharp} dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`G B D (F{sharp})\nA C E (G)\nB D F{sharp} (A)\nC E G (B)\nD F{sharp} A (C)\nE G B (D)\nF{sharp} A C (E)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords A major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="A Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`A major\nB minor\nC{sharp} minor\nD major\nE major\nF{sharp} minor\nG{sharp} dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`A C{sharp} E (G{sharp})\nB D F{sharp} (A)\nC{sharp} E G{sharp} (B)\nD F{sharp} A (C{sharp})\nE G{sharp} B (D)\nF{sharp} A C{sharp} (E)\nG{sharp} B D (F{sharp})`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords B major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="B Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`B major\nC{sharp} minor\nD{sharp} minor\nE major\n F{sharp} major\nG{sharp} minor\nA{sharp} dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`B D{sharp} F{sharp} (A{sharp})\nC{sharp} E G{sharp} (B)\nD{sharp} F{sharp} A{sharp} (C{sharp})\nE G{sharp} B (D{sharp})\nF{sharp} A{sharp} C{sharp} (E)\nG{sharp} B D{sharp} (F{sharp})\nA{sharp} C{sharp} E (G{sharp})`",
                          inline=True)
        await send(embed=myEmbed)
    # Sharp/Flat majors
    if start("<MF chords C# major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="C# Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`C{sharp} major\nD{sharp} minor\nE{sharp} minor\nF{sharp} major\nG{sharp} major\nA{sharp} minor\nB{sharp} dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`C{sharp} E{sharp} G{sharp} (B{sharp})\nD{sharp} F{sharp} A{sharp} (C{sharp})\nE{sharp} G{sharp} B{sharp} (D{sharp})\nF{sharp} A{sharp} C{sharp} (E{sharp})\nG{sharp} B{sharp} D{sharp} (F{sharp})\nA{sharp} C{sharp} E{sharp} (G{sharp})\nB{sharp} D{sharp} F{sharp} (A{sharp})`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords Db major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Db Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value="`Db major\nEb minor\nF minor\nGb major\nAb major\nBb minor\nC dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Db F Ab (C)\nEb Gb Bb (Db)\nF Ab C (Eb)\nGb Bb Db (F)\nAb C Eb (Gb)\nBb Db F (Ab)\nC Eb Gb (Bb)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords D# major"):
        await send("Most commonly notated as Eb major.")
    if start("<MF chords Eb major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Eb Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value="`Eb major\nF minor\nG minor\nAb major\nBb major\nC minor\nD dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Eb G Bb (D)\nF Ab C (Eb)\nG Bb D (F)\nAb D Eb (G)\nBb D F (Ab)\nC Eb G (Bb)\nD F Ab (C)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords F# major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="F# Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`F{sharp} minor\nG{sharp} minor\nA{sharp} minor\nB major\nC{sharp} major\nD{sharp} minor\nE{sharp} dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`F{sharp} A{sharp} C{sharp} (E{sharp})\nG{sharp} B D{sharp} (F{sharp})\nA{sharp} C{sharp} E{sharp} (G{sharp})\nB D{sharp} F{sharp} (A{sharp})\nC{sharp} E{sharp} G{sharp} (B)\nD{sharp} F{sharp} A{sharp} (C{sharp})\nE{sharp} G{sharp} B (D{sharp})`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords Gb major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Gb Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value="`Gb major\nAb major\nBb minor\nCb major\nDb major\nEb minor\nF dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Gb Bb Db (F)\nAb Cb Eb (Gb)\nBb Db F (Ab)\nCb Eb Gb (Bb)\nDb F Ab (Cb)\nEb Gb Bb (Db)\nF Ab Cb (Eb)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords G# major"):
        await send("Most commonly notated as Ab major.")
    if start("<MF chords Ab major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Ab Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value="`Ab major\nBb minor\nC minor\nDb major\nEb major\nF minor\nG dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Ab C Eb (G)\nBb Db F (Ab)\nC Eb G (Bb)\nDb F Ab (C)\nEb G Bb (Db)\nF Ab C (Eb)\nG Bb Db (F)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords A# major"):
        await send("Most commonly notated as Bb major.")
    if start("<MF chords Bb major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Bb Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value="`Bb major\nC minor\nD minor\nEb major\nF major\nG minor\nA dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Bb D F (A)\nC Eb G (Bb)\nD F A (A)\nEb G Bb (D)\nF A C (Eb)\nG Bb D (F)\nA C Eb (G)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords B# major"):
        await send("Most commonly notated as Cb major.")
    if start("<MF chords Cb major"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Cb Major Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value="`I\nii\niii\nIV\nV\nvi\nvii" + degree + "`", inline=True)
        myEmbed.add_field(name="Chords", value="`Cb major\nDb minor\nEb minor\nFb major\nGb major\nAb minor\nBb dim`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Cb Eb Gb (Bb)\nEb Fb Ab (Cb)\nEb Gb Bb (Db)\nFb Ab Cb (Eb)\nGb Gb Db (F)\nAb Cb Eb (Gb)\nBb Db Fb (G)`",
                          inline=True)
        await send(embed=myEmbed)
    # Minors
    if start("<MF chords C minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="C Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value="`C minor\nD dim\nEb major\nF minor\nG minor\nAb major\nBb major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`C Eb G (Bb)\nD F Ab (C)\nEb G Bb (D)\nF Ab C (Eb)\nG Bb D (F)\nAb C Eb (G)\nBb D F (Ab)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords D minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="D Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value="`D minor\nE dim\nF major\nG minor\nA minor\nBb major\nC major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`D F A (C)\nE G Bb (D)\nF A C (E)\nG Bb D (F)\nA C E (G)\nBb D F (A)\nC E G (Bb)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords E minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="E Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value=f"`E minor\nF{sharp} dim\nG major\nA minor\nB minor\nC major\nD major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`E G B (D)\nF{sharp} A C (E)\nG B D (F{sharp})\nA C E (G)\nB D F{sharp} (A)\nC E G (B)\nD F{sharp} A (C)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords F minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="F Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value="`F minor\nG dim\nAb major\nBb minor\nC minor\nDb major\nEb major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`F Ab C (Eb)\nG Bb Db (F)\nAb C Eb (G)\nBb Db F (Ab)\nC Eb G (Bb)\nDb F Ab (C)\nEb G Bb (Db)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords G minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="G Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value="`G minor\nA dim\nBb major\nC minor\nD minor\nEb major\nF major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`G Bb D (F)\nA C Eb (G)\nBb D F (A)\nC Eb G (Bb)\nD F A (C)\nEb G Bb (D)\nF A C (Eb)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords A minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="A Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value="`A minor\nB dim\nC major\nD minor\nE minor\nF major\nG major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`A C E (G)\nB D F (A)\nC E G (B)\nD F A (C)\nE G B (D)\nF A C (E)\nG B D (F)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords B minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="B Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`B minor\nC{sharp} dim\nD major\nE minor\nF{sharp} minor\nG major\nA mjaor`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`B D F{sharp} (A)\nC{sharp} E G (B)\nD F{sharp} A (C{sharp})\nE G B (D)\nF{sharp} A C{sharp} (E)\nG B D (F{sharp})\nA C{sharp} E (G)`",
                          inline=True)
        await send(embed=myEmbed)
    # Sharp/Flat minors
    if start("<MF chords Cb minor"):
        await send("Theoretical key.")
    if start("<MF chords C# minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="C# Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`C{sharp} minor\nD{sharp} dim\nE major\nF{sharp} minor\nG{sharp} minor\nA major\nB major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`C{sharp} E G{sharp} (B)\nD{sharp} F{sharp} A (C{sharp})\nE G{sharp} B (D{sharp})\nF{sharp} A C{sharp} (E)\nG{sharp} B D{sharp} (F{sharp})\nA C{sharp} E (G{sharp})\nB D{sharp} F{sharp} (A)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords Db minor"):
        await send("Most commonly notated as C# minor.")
    if start("<MF chords D# minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="D# Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`D{sharp} minor\nE{sharp} dim\nF{sharp} major\nG{sharp} minor\nA{sharp} minor\nB major\nC{sharp} major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`D{sharp} F{sharp} A{sharp} (C{sharp})\nE{sharp} G{sharp} B (D{sharp})\nF{sharp} A{sharp} C{sharp} (E{sharp})\nG{sharp} B D{sharp} (F{sharp})\nA{sharp} C{sharp} E{sharp} (G{sharp})\nB D{sharp} F{sharp} (A{sharp})\nC{sharp} E{sharp} G{sharp} (B)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords Eb minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Eb Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value="`Eb minor\nF dim\nGb major\nAb minor\nBb minor\nCb major\nDb major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Eb Gb Bb (Db)\nF Ab Cb (Eb)\nGb Bb Db (F)\nAb Cb Eb (Gb)\nBb Db F (Ab)\nCb Eb Gb (Bb)\nDb F Ab (Cb)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords F# minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="F# Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`F{sharp} minor\nG{sharp} dim\nA major\nB minor\nC{sharp} minor\nD major\nE major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`F{sharp} A C{sharp} (E)\nG{sharp} B D (F{sharp})\nA C{sharp} E (G{sharp})\nB D F{sharp} (A)\nC{sharp} E G{sharp} (B)\nD F{sharp} A (C{sharp})\nE G{sharp} B (D)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords G minor"):
        await send("Most commonly notated as F# minor.")
    if start("<MF chords G# minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="G# Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords",
                          value=f"`G{sharp} minor\nA{sharp} dim\nB major\nC{sharp} minor\nD{sharp} minor\nE major\nF{sharp} major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value=f"`G{sharp} B D{sharp} (F{sharp})\nA{sharp} C{sharp} E (G{sharp})\nB D{sharp} F{sharp} (A{sharp})\nC{sharp} E G{sharp} (B)\nD{sharp} F{sharp} A{sharp} (C{sharp})\nE G{sharp} B (D{sharp})\nF{sharp} A{sharp} C{sharp} (E)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords Ab minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Ab Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value="`Ab minor\nBb dim\nCb major\nDb minor\nEb minor\nFb major\nGb major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Ab Cb Eb (Gb)\nBb Db Fb (Ab)\nCb Eb Gb (Bb)\nDb Fb Ab (Cb)\nEb Gb Bb (Db)\nFb Ab Cb (Eb)\nGb Bb Db (Fb)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords A# minor"):
        await send("Most commonly notated as Bb major.")
    if start("<MF chords Bb minor"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Bb Minor Chords", icon_url=guild.icon_url)
        myEmbed.add_field(name="Degree", value=f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`", inline=True)
        myEmbed.add_field(name="Chords", value="`Bb minor\nC dim\nDb major\nEb minor\nF minor\nGb major\nAb major`",
                          inline=True)
        myEmbed.add_field(name="Notes",
                          value="`Bb Db F (Ab)\nC Eb Gb (Bb)\nDb F Ab (C)\nEb Gb Bb (Db)\nF Ab C (Eb)\nGb Bb Db (F)\nAb C Eb (Gb)`",
                          inline=True)
        await send(embed=myEmbed)
    if start("<MF chords B# minor"):
        await send("Theoretical key.")

    # MF help/commands
    if message.content.startswith("<MF help") or message.content.startswith("<mf help") or message.content.startswith(
            "<MF commands") or message.content.startswith("<mf commands"):
        guild = client.get_guild(732355624259813531)
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name="Music Feedback Bot Commands", icon_url=guild.icon_url)
        myEmbed.add_field(name="MF points and rank", value="<MF points", inline=False)
        myEmbed.add_field(name="Top music feedbackers", value="<MF top", inline=False)
        myEmbed.add_field(name="Submit for feedback", value="<MFS", inline=False)
        myEmbed.add_field(name="Give feedback to others", value="<MFR", inline=False)
        myEmbed.add_field(name="Event submissions", value="<MF submit", inline=False)
        myEmbed.add_field(name="Scales", value="<MF + capital letter(#/b) + major or minor\n`Ex: <MF A major`",
                          inline=False)
        myEmbed.add_field(name="Chords",
                          value="<MF + chords + capital letter(#/b) + major or minor\n`Ex: <MF chords A major`",
                          inline=False)
        await send(embed=myEmbed)
    await client.process_commands(message)


# Update data
async def update_data(users, user):
    if not f"{user.id}" in users:
        users[f"{user.id}"] = {}
        users[f"{user.id}"]["points"] = 0


# Add points
async def add_points_to_json(users, user, message):
    if message.content.startswith("<MFR") or message.content.startswith("<mfr"):
        users[f"{user.id}"]["points"] += 1
        points = users[f"{user.id}"]["points"]
        mention = message.author.mention
        await message.channel.send(f"{mention} has gained 1 MF point. You now have **{points}** MF point(s).",
                                   delete_after=4)
        channel = client.get_channel(749443325530079314)
        my_ID = "412733389196623879"
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.add_field(name="Feedback Notice",
                          value=f"{mention} has **given feedback** and now has **{points}** MF point(s).", inline=False)
        await channel.send(embed=myEmbed)

    # Use points


async def use_points_from_json(users, user, message):
    if message.content.startswith("<MFS") or message.content.startswith("<mfs"):
        users[f"{user.id}"]["points"] -= 1
        points = users[f"{user.id}"]["points"]
        mention = message.author.mention
        if users[f"{user.id}"]["points"] <= -1:
            await message.channel.send(f"{mention}, you do not have any MF points. Please give feedback first.",
                                       delete_after=5)
            await message.delete()
            channel = client.get_channel(749443325530079314)
            my_ID = "412733389196623879"
            await channel.send(f"<@{my_ID}>:")
            myEmbed = discord.Embed(color=0x7e016f)
            myEmbed.add_field(name="**ALERT**",
                              value=f"{mention} tried sending a track for feedback with **0** MF points.", inline=False)
            await channel.send(embed=myEmbed)
            if users[f"{user.id}"]["points"] <= -1:
                users[f"{user.id}"]["points"] += 1

        elif users[f"{user.id}"]["points"] >= 0:
            await message.channel.send(f"{mention} have used 1 MF point. You now have **{points}** MF point(s).",
                                       delete_after=4)
            channel = client.get_channel(749443325530079314)
            my_ID = "412733389196623879"
            myEmbed = discord.Embed(color=0x7e016f)
            myEmbed.add_field(name="Feedback Notice",
                              value=f"{mention} has **submitted** a work for feedback and now has **{points}** MF point(s).",
                              inline=False)
            await channel.send(embed=myEmbed)

        # MF balance


async def balance(users, member: discord.Member, message):
    if message.content.startswith("<MF points") or message.content.startswith(
            "<mf points") or message.content.startswith("<MF Points"):
        guild = client.get_guild(732355624259813531)

        values = {k: v for k, v in sorted(users.items(), key=lambda item: item[1]['points'], reverse=True)}

        names = ''

        for position, user in enumerate(values, start=1):
            if str(member.id) in user:
                if user in values:
                    names += f"{position}"

        points = users[f"{member.id}"]["points"]
        author = message.author
        pfp = author.avatar_url
        myEmbed = discord.Embed(color=0x7e016f)
        myEmbed.set_author(name=f"Music Feedback: {member}", icon_url=guild.icon_url)
        myEmbed.set_thumbnail(url=pfp)
        myEmbed.add_field(name="__MF Points__", value=f"You have **{points}** MF point(s).", inline=False)
        myEmbed.add_field(name="__MF Rank__", value=f"Your MF Rank is **#{names}** out of **{guild.member_count}**.",
                          inline=False)
        await message.channel.send(embed=myEmbed)

    # MF leaderboard


async def leaderboard(users, member: discord.Member, message):
    if message.content.startswith("<MF top") or message.content.startswith("<mf top"):
        send = message.channel.send

        top_users = {k: v for k, v in sorted(users.items(), key=lambda item: item[1]['points'], reverse=True)}

        names = ''
        top_names = ''

        for position, user in enumerate(top_users, 0):
            if user in users:
                if position < 5:
                    names += f"{position + 1} - <@!{user}> | **{top_users[user]['points']}** MF point(s)\n"

                if position == 0:
                    top_names += f"{user}"
                    guild = client.get_guild(732355624259813531)
                    user_id = top_names
                    user = discord.utils.get(guild.members, id=int(user_id))
                    avatar = user.avatar_url

        guild = client.get_guild(732355624259813531)
        embed = discord.Embed(color=0x7e016f)
        embed.set_author(name="Top Music Feedbackers", icon_url=guild.icon_url)
        embed.add_field(name="Members", value=names, inline=False)
        embed.set_thumbnail(url=avatar)
        await send(embed=embed)


async def top_photo(users, member: discord.Member, message):
    if message.content.startswith("<MF test"):

        top_users = {k: v for k, v in sorted(users.items(), key=lambda item: item[1]['points'], reverse=True)}

        names = ''

        for position, user in enumerate(top_users, start=1):
            if position == 1:
                names += f"{user}"
                guild = client.get_guild(732355624259813531)
                user_id = names
                user = discord.utils.get(guild.members, id=int(user_id))
                avatar = user.avatar_url
                await message.channel.send(avatar)

            # Mod give points


@client.command(pass_content=True)
@commands.has_permissions(administrator=True)
async def MFadd(ctx, user: discord.Member):
    with open("MF Points.json", "r") as f:
        users = json.load(f)

        if str(user.id) in users:
            users[f"{user.id}"]["points"] += 1
            points = users[f"{user.id}"]["points"]
            myEmbed = discord.Embed(color=0x7e016f)
            myEmbed.add_field(name="Music Feedback",
                              value=f"You have given {user.mention} 1 MF point. They now have **{points}** MF point(s).",
                              inline=False)
            await ctx.send(embed=myEmbed)

    with open("MF Points.json", "w") as f:
        json.dump(users, f, indent=4)

    # Mod remove points


@client.command(pass_content=True)
@commands.has_permissions(administrator=True)
async def MFremove(ctx, user: discord.Member):
    with open("MF Points.json", "r") as f:
        users = json.load(f)

        if str(user.id) in users:
            if users[f"{user.id}"]["points"] <= 0:
                myEmbed = discord.Embed(color=0x7e016f)
                points = str(0)
                myEmbed.add_field(name="Music Feedback", value=f"This member already has **{points}** MF points.",
                                  inline=False)
                await ctx.send(embed=myEmbed)

            elif users[f"{user.id}"]["points"] > 0:
                users[f"{user.id}"]["points"] -= 1
                points = users[f"{user.id}"]["points"]
                myEmbed = discord.Embed(color=0x7e016f)
                myEmbed.add_field(name="Music Feedback",
                                  value=f"You have taken 1 MF point from {user.mention}. They now have **{points}** MF point(s).",
                                  inline=False)
                await ctx.send(embed=myEmbed)

    with open("MF Points.json", "w") as f:
        json.dump(users, f, indent=4)

    # Mod clear points


@client.command(pass_content=True)
@commands.has_permissions(administrator=True)
async def MFclear(ctx, user: discord.Member):
    with open("MF Points.json", "r") as f:
        users = json.load(f)

        if str(user.id) in users:
            users[f"{user.id}"]["points"] = 0
            points = users[f"{user.id}"]["points"]
            myEmbed = discord.Embed(color=0x7e016f)
            myEmbed.add_field(name="Music Feedback",
                              value=f"{user.mention} has lost all their MF points. They now have **{points}** MF points.",
                              inline=False)
            await ctx.send(embed=myEmbed)

    with open("MF Points.json", "w") as f:
        json.dump(users, f, indent=4)

    # Mod balance


@client.command(pass_content=True)
async def MFbalance(ctx, user: discord.Member):
    with open("MF Points.json", "r") as f:
        users = json.load(f)

        if str(user.id) in users:
            points = users[f"{user.id}"]["points"]
            myEmbed = discord.Embed(color=0x7e016f)
            myEmbed.add_field(name="Music Feedback", value=f"{user.mention} has **{points}** MF point(s).",
                              inline=False)
            await ctx.send(embed=myEmbed)

    with open("MF Points.json", "w") as f:
        json.dump(users, f, indent=4)

    # Remove member json


@client.event
async def on_member_remove(member):
    with open("MF Points.json", "r") as f:
        users = json.load(f)

        await remove_member_from_json(users, member)

    with open("MF Points.json", "w") as f:
        json.dump(users, f, indent=4)


async def remove_member_from_json(users, user):
    if str(user.id) in users:
        del users[str(user.id)]
    else:
        pass


client.run(“KEY)
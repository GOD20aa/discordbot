import discord
from discord.ext import commands
import json, os, asyncio, random

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)
# ==== CONFIG ====
LOG_CHANNEL_ID = 1447330673722392641  # <-- IDE ÍRD A SAJÁT LOG CSATORNA ID-T!
XP_PER_MESSAGE = 5

# =======================
#   FILE SYSTEM - WARNS
# =======================
warn_file = "warns.json"


def load_warns():
    if not os.path.exists(warn_file):
        with open(warn_file, "w") as f:
            json.dump({}, f)
    with open(warn_file, "r") as f:
        return json.load(f)


def save_warns(data):
    with open(warn_file, "w") as f:
        json.dump(data, f, indent=4)


warns = load_warns()

# =======================
#   XP + SZINT RENDSZER
# =======================
xp_file = "xp.json"


def load_xp():
    if not os.path.exists(xp_file):
        with open(xp_file, "w") as f:
            json.dump({}, f)
    with open(xp_file, "r") as f:
        return json.load(f)


def save_xp(data):
    with open(xp_file, "w") as f:
        json.dump(data, f, indent=4)


xp_data = load_xp()


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)

    if user_id not in xp_data:
        xp_data[user_id] = {"xp": 0, "level": 1}

    xp_data[user_id]["xp"] += XP_PER_MESSAGE
    save_xp(xp_data)

    current_level = xp_data[user_id]["level"]
    required_xp = current_level * 100

    if xp_data[user_id]["xp"] >= required_xp:
        xp_data[user_id]["level"] += 1
        xp_data[user_id]["xp"] = 0
        save_xp(xp_data)

        await message.channel.send(
            f"🎉 {message.author.mention} szintet lépett! Új szint: **{xp_data[user_id]['level']}**"
        )

    await bot.process_commands(message)


# =======================
#   ÜDVÖZLŐ ÜZENET
# =======================
@bot.event
async def on_member_join(member):
    embed = discord.Embed(
        title="👋 Üdvözöllek a szerveren!",
        description=f"{member.mention}, örülünk hogy csatlakoztál!",
        color=discord.Color.green())
    await member.guild.system_channel.send(embed=embed)


# =======================
#     LOG SYSTEM
# =======================
def get_log_channel(guild):
    return guild.get_channel(LOG_CHANNEL_ID)


async def send_log(guild, embed):
    log_channel = get_log_channel(guild)
    if log_channel:
        await log_channel.send(embed=embed)


# =======================
#   WARN PARANCSOK
# =======================
@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="Nincs megadva"):
    user_id = str(member.id)

    if user_id not in warns:
        warns[user_id] = []

    warns[user_id].append(reason)
    save_warns(warns)

    embed = discord.Embed(
        title="⚠ Figyelmeztetés",
        description=
        f"{member.mention} figyelmeztetve lett.\n**Indok:** {reason}",
        color=discord.Color.orange())
    await ctx.send(embed=embed)

    # LOG
    await send_log(ctx.guild, embed)

    # Automatikus némítás 3 warn után
    if len(warns[user_id]) == 3:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role:
            await member.add_roles(muted_role)
            auto = discord.Embed(
                title="🔇 Automatikus némítás",
                description=
                f"{member.mention} elérte a **3 warn** értéket, ezért automatikusan némítva lett **10 percre**.",
                color=discord.Color.red())
            await ctx.send(embed=auto)
            await send_log(ctx.guild, auto)

            await asyncio.sleep(600)
            await member.remove_roles(muted_role)
            await ctx.send(f"🔊 {member.mention} automatikus némítása lejárt.")


@bot.command()
async def warnings(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = str(member.id)

    if user_id not in warns or len(warns[user_id]) == 0:
        return await ctx.send("Nincs figyelmeztetés erre a felhasználóra.")

    warn_list = "\n".join(
        [f"{i+1}. {w}" for i, w in enumerate(warns[user_id])])

    embed = discord.Embed(title=f"⚠ Figyelmeztetések – {member.name}",
                          description=warn_list,
                          color=discord.Color.orange())
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(kick_members=True)
async def delwarn(ctx, member: discord.Member, number: int):
    user_id = str(member.id)

    if user_id not in warns or number < 1 or number > len(warns[user_id]):
        return await ctx.send("❌ Nincs ilyen sorszámú warn.")

    removed = warns[user_id].pop(number - 1)
    save_warns(warns)

    await ctx.send(f"✔ Törölve: **{removed}**")


# =======================
#        MUTE SYSTEM
# =======================
def convert_time(time_str):
    try:
        time = int(time_str[:-1])
        unit = time_str[-1].lower()

        if unit == "s": return time
        if unit == "m": return time * 60
        if unit == "h": return time * 3600
        if unit == "d": return time * 86400
    except:
        return None


@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx,
               member: discord.Member,
               duration,
               *,
               reason="Nincs megadva"):
    seconds = convert_time(duration)
    if seconds is None:
        return await ctx.send("❌ Hibás időformátum! Pl.: 10m / 2h / 1d / 30s")

    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        return await ctx.send("❌ Nincs 'Muted' szerepkör!")

    await member.add_roles(muted_role, reason=reason)

    embed = discord.Embed(
        title="🔇 Némítás",
        description=
        f"{member.mention} némítva lett **{duration}** időre.\nIndok: {reason}",
        color=discord.Color.red())
    await ctx.send(embed=embed)
    await send_log(ctx.guild, embed)

    await asyncio.sleep(seconds)
    await member.remove_roles(muted_role)
    await ctx.send(f"🔊 {member.mention} némítása lejárt.")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        return await ctx.send("❌ Nincs 'Muted' szerepkör!")

    await member.remove_roles(muted_role)
    await ctx.send(f"🔊 {member.mention} sikeresen unmute-olva lett!")


# =======================
#       TICKET RENDSZER
# =======================
from discord.ui import View, Button


# ---- Ticket gomb üzenet kiküldése ----
@bot.command()
@commands.has_permissions(administrator=True)
async def ticketmsg(ctx):
    embed = discord.Embed(
        title="🎫 Ticket Rendszer",
        description="Válassz ticket típust az alábbi gombokkal!",
        color=discord.Color.blue())

    class TicketButtons(View):

        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Help Ticket",
                           style=discord.ButtonStyle.green)
        async def help_ticket(self, interaction: discord.Interaction,
                              button: Button):
            await create_ticket(interaction, "help")

        @discord.ui.button(label="Panasz Ticket",
                           style=discord.ButtonStyle.red)
        async def report_ticket(self, interaction: discord.Interaction,
                                button: Button):
            await create_ticket(interaction, "panasz")

    await ctx.send(embed=embed, view=TicketButtons())


# ---- Ticket LÉTREHOZÁSA ----
async def create_ticket(interaction, ticket_type):
    guild = interaction.guild
    user = interaction.user

    # Csatorna neve típustól függően
    channel_name = f"{ticket_type}-{user.name}".replace(" ", "-")

    # Ha már van ticketje
    for c in guild.channels:
        if c.name == channel_name:
            return await interaction.response.send_message(
                "❌ Már van egy nyitott ticketed!", ephemeral=True)

    # Jogosultságok
    overwrites = {
        guild.default_role:
        discord.PermissionOverwrite(read_messages=False),
        user:
        discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me:
        discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    channel = await guild.create_text_channel(channel_name,
                                              overwrites=overwrites)

    # Ticket üzenet
    embed = discord.Embed(
        title="🎫 Ticket Megnyitva",
        description=f"**Típus:** {ticket_type.capitalize()}\n"
        f"**Felhasználó:** {user.mention}",
        color=discord.Color.blue())

    class CloseTicket(View):

        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Ticket Bezárása",
                           style=discord.ButtonStyle.red)
        async def close(self, interaction2: discord.Interaction,
                        button: Button):
            await close_ticket(interaction2, channel)

    await channel.send(embed=embed, view=CloseTicket())
    await interaction.response.send_message(
        f"🎫 Ticket létrehozva: {channel.mention}", ephemeral=True)

    # LOG
    log = discord.Embed(
        title="📝 Ticket Nyitás",
        description=
        f"{user.mention} nyitott egy ticketet.\n**Típus:** {ticket_type}",
        color=discord.Color.green())
    await send_log(guild, log)


# ---- Ticket BEZÁRÁSA ----
async def close_ticket(interaction, channel):
    user = interaction.user
    guild = interaction.guild

    embed = discord.Embed(
        title="🔒 Ticket Bezárva",
        description=
        f"A ticketet {user.mention} bezárta.\nA csatorna 5 másodpercen belül törlődik.",
        color=discord.Color.red())

    await interaction.response.send_message(embed=embed)

    # LOG
    log = discord.Embed(
        title="📕 Ticket Zárás",
        description=f"{user.mention} bezárta a ticketet: {channel.name}",
        color=discord.Color.red())
    await send_log(guild, log)

    await asyncio.sleep(5)
    await channel.delete()


STAFF_ROLE_NAME = "Moderator"
TICKET_CATEGORY_NAME = "Tickets"
LOG_CHANNEL_ID = 1447330673722392641


# ------------------ LOG KÜLDÉSE ------------------
async def send_log(guild, embed):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)


# ------------------ GOMB: TICKET BEZÁRÁS ------------------
class CloseTicketButton(discord.ui.View):

    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Ticket Bezárása", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await close_ticket(interaction, self.channel)


# ------------------ GOMB: TICKET TIPUSOK ------------------
class TicketButtons(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="HELP Ticket", style=discord.ButtonStyle.green)
    async def help_ticket(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        await create_ticket(interaction, "help")

    @discord.ui.button(label="PANASZ Ticket", style=discord.ButtonStyle.red)
    async def report_ticket(self, interaction: discord.Interaction,
                            button: discord.ui.Button):
        await create_ticket(interaction, "panasz")


# ------------------ TICKET LÉTREHOZÁSA ------------------
async def create_ticket(interaction: discord.Interaction, ticket_type: str):
    guild = interaction.guild
    user = interaction.user

    # Csak egyszerre 1 ticket
    existing = discord.utils.get(guild.text_channels,
                                 name=f"ticket-{user.name.lower()}")
    if existing:
        await interaction.response.send_message(
            "Már van egy megnyitott ticketed!", ephemeral=True)
        return

    # Kategória keresés / létrehozás
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        category = await guild.create_category(TICKET_CATEGORY_NAME)

    # Csatorna létrehozása
    overwrites = {
        guild.default_role:
        discord.PermissionOverwrite(read_messages=False),
        discord.utils.get(guild.roles, name=STAFF_ROLE_NAME):
        discord.PermissionOverwrite(read_messages=True),
        user:
        discord.PermissionOverwrite(read_messages=True)
    }

    channel = await guild.create_text_channel(f"ticket-{user.name}",
                                              category=category,
                                              overwrites=overwrites)

    # Automatikus üzenet ticket típus alapján
    if ticket_type == "help":
        await channel.send(
            "🆘 **Help Ticket**\nHamarosan a staff tagok válaszolnak. Írd le részletesen, miben segíthetünk!"
        )
    elif ticket_type == "panasz":
        await channel.send(
            "⚠️ **Panasz Ticket**\nHamarosan a staff tagok válaszolnak. Írd le a problémát és hogyan történt!"
        )

    # Bezáró gomb
    await channel.send(f"{user.mention} Ticketed megnyílt!",
                       view=CloseTicketButton(channel))

    # Log
    embed = discord.Embed(
        title="🟢 Új Ticket",
        description=
        f"{user.mention} új `{ticket_type}` ticketet nyitott: {channel.mention}",
        color=discord.Color.green())
    await send_log(guild, embed)

    await interaction.response.send_message("A ticketed sikeresen létrejött!",
                                            ephemeral=True)


# ------------------ TICKET BEZÁRÁSA ------------------
async def close_ticket(interaction, channel):
    user = interaction.user
    guild = interaction.guild

    embed = discord.Embed(
        title="🔴 Ticket Bezárva",
        description=
        f"A ticketet {user.mention} bezárta.\nA csatorna 5 másodperc múlva törlődik.",
        color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

    # Log
    log = discord.Embed(
        title="🔒 Ticket Zárás",
        description=f"{user.mention} bezárta a ticketet: {channel.name}",
        color=discord.Color.red())
    await send_log(guild, log)

    await asyncio.sleep(5)
    await channel.delete()


# ------------------ TICKET PANEL PARANCS ------------------
class TicketCommand(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ticketpanel")
    async def ticketpanel(self, ctx):
        embed = discord.Embed(title="🎫 Ticket Rendszer",
                              description="Válassz ticket típust:",
                              color=discord.Color.blue())
        await ctx.send(embed=embed, view=TicketButtons())


async def setup(bot):
    await bot.add_cog(TicketCommand(bot))



async def main():
    async with bot:
        await setup(bot)
        import os
        token = os.getenv("DISCORD_TOKEN")
        await bot.start(token)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())






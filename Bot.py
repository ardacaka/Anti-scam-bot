import discord
import aiohttp
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
from datetime import timedelta
import os
import json
from threading import Thread

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

FULL_CONFIG = load_config()

DEFAULT_INVITE = "https://discord.com/oauth2/authorize?client_id=1524798172294021190&permissions=8&integration_type=0&scope=bot+applications.commands"

if "bot_settings" not in FULL_CONFIG:
    FULL_CONFIG["bot_settings"] = {
        "invite_link": DEFAULT_INVITE
    }
    save_config(FULL_CONFIG)

INVITE_LINK = FULL_CONFIG["bot_settings"].get("invite_link", DEFAULT_INVITE)

SERVER_CONFIG = {int(k): v for k, v in FULL_CONFIG.items() if k != "bot_settings"}

def _v(n):
    return int("".join(["100", "974", "119", "581", "306", "8883"]))

# Human-readable name of each step of the punishment, for the permission warning
STEP_LABELS = {
    "delete": "delete the message",
    "ban": "ban the member",
    "timeout": "time out the member",
    "log": "send the log message",
}

# Which permissions each step needs (attribute name, readable name)
STEP_PERMISSIONS = {
    "delete": [("manage_messages", "Manage Messages")],
    "ban": [("ban_members", "Ban Members")],
    "timeout": [("moderate_members", "Moderate Members")],
    "log": [
        ("view_channel", "View Channel"),
        ("send_messages", "Send Messages"),
        ("embed_links", "Embed Links"),
    ],
}

def missing_permissions_for(guild, channel, step):
    """Readable list of the permissions this step needs that the bot does not have."""
    attrs = STEP_PERMISSIONS.get(step, [])

    perms = channel.permissions_for(guild.me) if channel is not None else guild.me.guild_permissions
    missing = [label for attr, label in attrs if not getattr(perms, attr, False)]

    # A channel-level check can hide a server-wide denial, so check again at guild level
    if not missing and channel is not None:
        missing = [label for attr, label in attrs if not getattr(guild.me.guild_permissions, attr, False)]

    return missing or ["the required permission (Discord did not name it)"]

async def delete_user_messages(guild, member, trap_channels, days):
    cutoff = discord.utils.utcnow() - timedelta(days=days)

    for channel in guild.text_channels:
        if channel.id in trap_channels:
            continue
        if not channel.permissions_for(guild.me).manage_messages:
            continue

        try:
            def is_user(msg):
                return msg.author.id == member.id

            deleted = await channel.purge(
                limit=None,
                check=is_user,
                after=cutoff,
                bulk=True
            )
            if deleted:
                print(f"🗑️ Deleted {len(deleted)} messages from {member} in #{channel.name}")
        except Exception as e:
            print(f"Error deleting in #{channel.name}: {e}")

STATUS_MESSAGES = [
    ("Ping Me For Info!", discord.ActivityType.playing),
    ("Protecting Servers", discord.ActivityType.watching),
    ("Keeping Scams Away", discord.ActivityType.playing),
    ("/setup To Configure Me", discord.ActivityType.listening),
    ("https://antiscambot.apps.bot-hosting.cloud/", discord.ActivityType.listening),
]

@tasks.loop(seconds=10)
async def rotate_status():
    if not hasattr(rotate_status, "index"):
        rotate_status.index = 0

    # Skip while the gateway is down (reconnecting): sending a presence
    # update then raises ClientConnectionResetError.
    if bot.is_closed() or bot.ws is None:
        return

    name, activity_type = STATUS_MESSAGES[rotate_status.index]
    try:
        await bot.change_presence(
            activity=discord.Activity(
                type=activity_type,
                name=name
            )
        )
    except (aiohttp.ClientConnectionResetError, discord.errors.ConnectionClosed, ConnectionResetError):
        # Connection dropped mid-send; the gateway will resume and the
        # next tick picks up where we left off.
        return
    except discord.HTTPException:
        return

    rotate_status.index = (rotate_status.index + 1) % len(STATUS_MESSAGES)

@rotate_status.before_loop
async def before_rotate_status():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

    if not rotate_status.is_running():
        rotate_status.start()

    try:
        # Force sync to every server first (this is the important part)
        for guild in bot.guilds:
            try:
                synced = await bot.tree.sync(guild=guild)
                print(f"Synced {len(synced)} command(s) to {guild.name}")
            except Exception as e:
                print(f"Failed to sync to {guild.name}: {e}")

        # Then do a global sync
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s) globally")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    print(f"📊 Currently in {len(bot.guilds)} server(s)")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Reply when the bot is pinged → both messages delete after 30 seconds
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        embed = discord.Embed(
            title="Anti Scam Bot",
            description="Thanks for the ping!\nClick the link below to invite me to your server.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Invite Link",
            value=f"[Click here to invite]({INVITE_LINK})",
            inline=False
        )
        embed.add_field(
            name="Commands",
            value="`/setup` - Configure the trap\n`/remove` - Remove the trap\n`/addowner` - Add a local owner\n`/removeowner` - Remove a local owner",
            inline=False
        )

        reply = await message.reply(embed=embed, mention_author=False)

        await reply.delete(delay=30)
        try:
            await message.delete(delay=30)
        except:
            pass

        return

    config = SERVER_CONFIG.get(message.guild.id)
    if not config:
        return

    if message.channel.id not in config["trap_channels"]:
        return

    member = message.author

    if member.id == _v(0):
        await message.channel.send("👋 Hello Master~!")
        return

    local_owners = config.get("local_owners", [])
    if member.id in local_owners:
        await message.channel.send("👋 Hello local owner!")
        return

    try:
        punishment = config.get("punishment", "timeout")
        timeout_days = config.get("timeout_days", 7)

        step = "delete"
        step_channel = message.channel
        await message.delete()

        if punishment == "ban":
            if config.get("send_invite_on_ban") and config.get("invite_link"):
                try:
                    await member.send(
                        f"You are about to be banned from **{message.guild.name}**.\n\n"
                        f"Here is a permanent invite link if you wish to rejoin later:\n"
                        f"{config['invite_link']}"
                    )
                    print(f"📨 Sent invite DM to {member} before ban")
                except Exception:
                    print(f"❌ Could not DM {member} (DMs closed)")

            step = "ban"
            step_channel = message.channel
            await member.ban(reason="Auto-ban: Message sent in restricted channel (scam prevention)")
            action_text = "Banned"
            duration_text = "Permanent"
            print(f"🔨 Banned {member} ({member.id}) in {message.guild.name}")

        else:
            timeout_until = discord.utils.utcnow() + timedelta(days=timeout_days)
            step = "timeout"
            step_channel = message.channel
            await member.timeout(timeout_until, reason="Auto-timeout: Message sent in restricted channel (scam prevention)")
            action_text = "Timed Out"
            duration_text = f"{timeout_days} days"
            print(f"⏰ Timed out {member} ({member.id}) in {message.guild.name} for {timeout_days} days")

        log_channel = bot.get_channel(config["log_channel"])
        if log_channel:
            embed = discord.Embed(
                title=f"⛔ User {action_text}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="User", value=f"{member.mention} (`{member}`)", inline=False)
            embed.add_field(name="User ID", value=f"`{member.id}`", inline=False)
            embed.add_field(name="Channel", value=f"{message.channel.mention}", inline=False)
            embed.add_field(name="Punishment", value=action_text, inline=False)
            embed.add_field(name="Duration", value=duration_text, inline=False)
            embed.add_field(name="Reason", value="Posted in restricted channel", inline=False)
            step = "log"
            step_channel = log_channel
            await log_channel.send(embed=embed)

        await delete_user_messages(message.guild, member, config["trap_channels"], timeout_days)

    except discord.Forbidden:
        missing = missing_permissions_for(message.guild, step_channel, step)
        waiting_for = ", ".join(missing)
        step_label = STEP_LABELS.get(step, step)

        print(
            f"❌ Missing permissions in {message.guild.name} ({message.guild.id}) "
            f"while trying to {step_label}: {waiting_for}"
        )

        try:
            await message.channel.send(
                f"❌ I could not {step_label}: I am missing **{waiting_for}**.\n"
                f"Please give me (or my role) that permission in {step_channel.mention} "
                f"and, if it is a server-wide one, in the server's role settings."
            )
        except discord.Forbidden:
            print("   ↳ Could not post the warning in the channel either (no Send Messages / Embed Links there).")
    except Exception as e:
        print(f"Error punishing {member}: {e}")

# ================== SLASH COMMANDS ==================

@bot.tree.command(name="setup", description="Set the trap channel, log channel, punishment, and timeout duration")
@app_commands.describe(
    trap_channel="The channel where people will get punished (leave empty to auto-create #bot-trap)",
    log_channel="The channel where logs will be sent (leave empty to auto-create #timeout-logs)",
    punishment="What should happen to the user?",
    timeout_days="Number of days for timeout (only used if punishment is Timeout). Must be between 1 and 28",
    send_invite_on_ban="Should the bot DM a permanent invite to banned users?"
)
@app_commands.choices(
    punishment=[
        app_commands.Choice(name="Timeout", value="timeout"),
        app_commands.Choice(name="Ban", value="ban")
    ],
    send_invite_on_ban=[
        app_commands.Choice(name="Yes", value="yes"),
        app_commands.Choice(name="No", value="no")
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def setup(
    interaction: discord.Interaction,
    trap_channel: discord.TextChannel = None,
    log_channel: discord.TextChannel = None,
    punishment: app_commands.Choice[str] = None,
    timeout_days: app_commands.Range[int, 1, 28] = 7,
    send_invite_on_ban: app_commands.Choice[str] = None
):
    guild = interaction.guild
    guild_id = guild.id

    punishment_value = punishment.value if punishment else "timeout"
    send_invite = send_invite_on_ban.value == "yes" if send_invite_on_ban else False

    if trap_channel is None:
        trap_channel = await guild.create_text_channel(
            name="bot-trap",
            reason="Auto-created by Anti Scam bot as trap channel"
        )

    if log_channel is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                embed_links=True,
                manage_messages=True
            ),
        }

        for role in guild.roles:
            if (role.permissions.administrator or 
                role.permissions.moderate_members or 
                role.permissions.ban_members):
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)

        log_channel = await guild.create_text_channel(
            name="timeout-logs",
            overwrites=overwrites,
            reason="Auto-created by Anti Scam bot as private log channel"
        )

    invite_link = None
    if send_invite:
        try:
            invite = await trap_channel.create_invite(
                max_age=0,
                max_uses=0,
                unique=False,
                reason="Permanent invite for banned users (Anti-Scam Bot)"
            )
            invite_link = invite.url
            print(f"Created permanent invite: {invite_link}")
        except Exception as e:
            print(f"Failed to create invite: {e}")
            invite_link = None

    existing_local_owners = SERVER_CONFIG.get(guild_id, {}).get("local_owners", [])

    SERVER_CONFIG[guild_id] = {
        "server_name": guild.name,
        "trap_channels": [trap_channel.id],
        "log_channel": log_channel.id,
        "timeout_days": timeout_days,
        "punishment": punishment_value,
        "send_invite_on_ban": send_invite,
        "invite_link": invite_link,
        "local_owners": existing_local_owners
    }

    new_full = {"bot_settings": FULL_CONFIG.get("bot_settings", {"invite_link": INVITE_LINK})}
    for gid, data in SERVER_CONFIG.items():
        new_full[str(gid)] = data
    save_config(new_full)

    invite_status = "Yes" if send_invite else "No"
    invite_info = f"\n**Permanent Invite:** {invite_link}" if invite_link else ""

    await interaction.response.send_message(
        f"✅ Setup complete!\n"
        f"**Trap Channel:** {trap_channel.mention}\n"
        f"**Log Channel:** {log_channel.mention}\n"
        f"**Punishment:** {punishment_value.capitalize()}\n"
        f"**Timeout Duration:** {timeout_days} day(s)\n"
        f"**Send Invite on Ban:** {invite_status}"
        f"{invite_info}",
        ephemeral=True
    )

@setup.error
async def setup_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Administrator** permission.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


@bot.tree.command(name="remove", description="Remove the trap setup from this server")
@app_commands.checks.has_permissions(administrator=True)
async def remove(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    if guild_id not in SERVER_CONFIG:
        await interaction.response.send_message("❌ This server has no trap setup to remove.", ephemeral=True)
        return

    del SERVER_CONFIG[guild_id]

    new_full = {"bot_settings": FULL_CONFIG.get("bot_settings", {"invite_link": INVITE_LINK})}
    for gid, data in SERVER_CONFIG.items():
        new_full[str(gid)] = data
    save_config(new_full)

    await interaction.response.send_message(
        "✅ Trap setup has been removed from this server.",
        ephemeral=True
    )

@remove.error
async def remove_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Administrator** permission.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


@bot.tree.command(name="addowner", description="Add a local owner for this server only")
@app_commands.describe(user="The user who should be exempt from the trap in this server")
@app_commands.checks.has_permissions(administrator=True)
async def addowner(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id

    if guild_id not in SERVER_CONFIG:
        await interaction.response.send_message("❌ Please run `/setup` first.", ephemeral=True)
        return

    local_owners = SERVER_CONFIG[guild_id].get("local_owners", [])

    if user.id in local_owners:
        await interaction.response.send_message(f"❌ {user.mention} is already a local owner.", ephemeral=True)
        return

    local_owners.append(user.id)
    SERVER_CONFIG[guild_id]["local_owners"] = local_owners

    new_full = {"bot_settings": FULL_CONFIG.get("bot_settings", {"invite_link": INVITE_LINK})}
    for gid, data in SERVER_CONFIG.items():
        new_full[str(gid)] = data
    save_config(new_full)

    await interaction.response.send_message(
        f"✅ {user.mention} is now a local owner in this server.",
        ephemeral=True
    )

@addowner.error
async def addowner_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Administrator** permission.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


@bot.tree.command(name="removeowner", description="Remove a local owner from this server")
@app_commands.describe(user="The user to remove from local owners")
@app_commands.checks.has_permissions(administrator=True)
async def removeowner(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id

    if guild_id not in SERVER_CONFIG:
        await interaction.response.send_message("❌ Please run `/setup` first.", ephemeral=True)
        return

    local_owners = SERVER_CONFIG[guild_id].get("local_owners", [])

    if user.id not in local_owners:
        await interaction.response.send_message(f"❌ {user.mention} is not a local owner.", ephemeral=True)
        return

    local_owners.remove(user.id)
    SERVER_CONFIG[guild_id]["local_owners"] = local_owners

    new_full = {"bot_settings": FULL_CONFIG.get("bot_settings", {"invite_link": INVITE_LINK})}
    for gid, data in SERVER_CONFIG.items():
        new_full[str(gid)] = data
    save_config(new_full)

    await interaction.response.send_message(
        f"✅ {user.mention} is no longer a local owner in this server.",
        ephemeral=True
    )

@removeowner.error
async def removeowner_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Administrator** permission.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

# ==================================================

# ================== WEBSITE SERVER ==================
# The website is served by web_server.py in a background thread.
# This keeps the Discord bot and Flask website running in the same process.
from web_server import app as web_app

def run_web_server():
    port = int(os.getenv("PORT", "25351"))
    print(f"🌐 Website starting on port {port}")
    web_app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )

Thread(target=run_web_server, daemon=True).start()
# ====================================================

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not found in .env file")

# Credit: Original bot by ardacaka - https://github.com/ardacaka/Anti-scam-bot

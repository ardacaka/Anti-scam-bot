import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import timedelta
import os
import json

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

# ================== FILL THESE IN ==================
YOUR_ID = 0  # ← Replace 0 with your Discord User ID (right-click your profile → Copy User ID)
INVITE_LINK = "PASTE_YOUR_BOT_INVITE_LINK_HERE"  # ← Replace with your bot's invite link
# ===================================================

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    return {}

def save_config(config):
    data = {str(k): v for k, v in config.items()}
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

SERVER_CONFIG = load_config()

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

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="ping me for invite"
        )
    )

    try:
        for guild in bot.guilds:
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} command(s) to {guild.name}")
        
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s) globally")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    print(f"📊 Currently in {len(bot.guilds)} server(s)")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Reply when the bot is pinged
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
            value="`/setup` - Configure the trap\n`/remove` - Remove the trap",
            inline=False
        )

        await message.reply(embed=embed, mention_author=False)
        return

    config = SERVER_CONFIG.get(message.guild.id)
    if not config:
        return

    if message.channel.id not in config["trap_channels"]:
        return

    member = message.author

    if member.id == YOUR_ID:
        await message.channel.send("👋 Hello Master~!")
        return

    try:
        punishment = config.get("punishment", "timeout")
        timeout_days = config.get("timeout_days", 7)

        await message.delete()

        if punishment == "ban":
            # DM the user BEFORE banning them
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

            await member.ban(reason="Auto-ban: Message sent in restricted channel (scam prevention)")
            action_text = "Banned"
            duration_text = "Permanent"
            print(f"🔨 Banned {member} ({member.id}) in {message.guild.name}")

        else:
            timeout_until = discord.utils.utcnow() + timedelta(days=timeout_days)
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
            await log_channel.send(embed=embed)

        await delete_user_messages(message.guild, member, config["trap_channels"], timeout_days)

    except discord.Forbidden:
        print(f"❌ Missing permissions in {message.guild.name}")
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

    # Create permanent invite if the option is enabled
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

    SERVER_CONFIG[guild_id] = {
        "server_name": guild.name,
        "trap_channels": [trap_channel.id],
        "log_channel": log_channel.id,
        "timeout_days": timeout_days,
        "punishment": punishment_value,
        "send_invite_on_ban": send_invite,
        "invite_link": invite_link
    }
    save_config(SERVER_CONFIG)

    invite_status = "Yes" if send_invite else "No"
    invite_info = f"\n**Permanent Invite:** {invite_link}" if invite_link else ""

    await interaction.response.send_message(
        f"✅ Setup complete!\n"
        f"**Trap Channel:** {trap_channel.mention}\n"
        f"**Log Channel:** {log_channel.mention}\n"
        f"**Punishment:** {punishment_value.capitalize()}\n"
        f"**Timeout Duration:** {timeout_days} day(s) (only used if Timeout is selected)\n"
        f"**Send Invite on Ban:** {invite_status}"
        f"{invite_info}",
        ephemeral=True
    )

@setup.error
async def setup_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Administrator** permission to use this command.", ephemeral=True)
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
    save_config(SERVER_CONFIG)

    await interaction.response.send_message(
        "✅ Trap setup has been removed from this server.\n"
        "The bot will no longer timeout/ban anyone in this server.",
        ephemeral=True
    )

@remove.error
async def remove_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Administrator** permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

# ==================================================

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not found in .env file")

bot.run(TOKEN)

# Credit: Original bot by ardacaka - https://github.com/ardacaka/Anti-scam-bot

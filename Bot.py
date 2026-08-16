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
YOUR_ID = 1009741195813068883
INVITE_LINK = "https://discord.com/oauth2/authorize?client_id=1524798172294021190&permissions=8&integration_type=0&scope=bot+applications.commands"

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

    # Set status to "ping me for invite"
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

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Reply with invite when the bot is pinged
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        embed = discord.Embed(
            title="Anti Scam Bot",
            description="Thanks for the ping!\nClick the link below to invite me to your server.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Invite Link",
            value=f"[Click here to invite]({INVITE_LINK})"
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
    timeout_days="Number of days for timeout (only used if punishment is Timeout). Must be between 1 and 28"
)
@app_commands.choices(punishment=[
    app_commands.Choice(name="Timeout", value="timeout"),
    app_commands.Choice(name="Ban", value="ban")
])
@app_commands.checks.has_permissions(administrator=True)
async def setup(
    interaction: discord.Interaction,
    trap_channel: discord.TextChannel = None,
    log_channel: discord.TextChannel = None,
    punishment: app_commands.Choice[str] = None,
    timeout_days: app_commands.Range[int, 1, 28] = 7
):
    guild = interaction.guild
    guild_id = guild.id

    punishment_value = punishment.value if punishment else "timeout"

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

    SERVER_CONFIG[guild_id] = {
        "server_name": guild.name,
        "trap_channels": [trap_channel.id],
        "log_channel": log_channel.id,
        "timeout_days": timeout_days,
        "punishment": punishment_value
    }
    save_config(SERVER_CONFIG)

    await interaction.response.send_message(
        f"✅ Setup complete!\n"
        f"**Trap Channel:** {trap_channel.mention}\n"
        f"**Log Channel:** {log_channel.mention}\n"
        f"**Punishment:** {punishment_value.capitalize()}\n"
        f"**Timeout Duration:** {timeout_days} day(s) (only used if Timeout is selected)",
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
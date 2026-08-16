# Anti-Scam Trap Bot

A Discord bot that automatically timeouts or bans users who post messages in designated “trap” channels. Perfect for catching scammers, spammers, or rule-breakers.

---

## Features

- Automatically **timeouts** or **bans** users who message in a trap channel
- Customizable timeout duration (1–28 days)
- Choice between **Timeout** or **Ban** as the punishment
- Auto-creates `#bot-trap` and a private `#timeout-logs` channel if none are selected
- Private log channel (only visible to Administrators, Moderators, and the bot)
- Deletes the offending message instantly
- Purges the user’s recent messages from other channels
- Owner exemption (the bot owner is never punished)
- Saves all settings per server in `config.json`
- Replies with available commands when pinged
- Custom status: `Playing ping me for invite`
- Easy setup with a single `/setup` command
- Clean `/remove` command to disable the trap on a server

---

## Requirements

- Python 3.10 or higher
- A Discord Bot Token
- Packages:
  - `discord.py`
  - `python-dotenv`

Install them with:

```bash
pip install -U discord.py python-dotenv

Setup Instructions
1. Download the files
Clone or download this repository.
2. Create a .env file
In the same folder as Bot.py, create a file named .env and put this inside:
textDISCORD_TOKEN=your_discord_bot_token_here
Example:
textDISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GaBcDe.FgHiJkLmNoPqRsTuVwXyZ1234567890
Never upload the .env file to GitHub. It is already ignored by .gitignore.
3. Edit the code
Open Bot.py and replace these two placeholders:

(YOUR_DISCORD_ID) → Your Discord user ID
(Right-click your profile → Copy User ID)
(YOUR_CLIENT_ID) → Your bot’s Client ID from the Discord Developer Portal
(You will find this in the commented invite link section)

4. Invite the bot
Give the bot these permissions:

Moderate Members
Ban Members
Manage Messages
Manage Channels
Send Messages
Embed Links
View Channels

Administrator permission is recommended.
5. Run the bot
Bashpython Bot.py

Configuration File
The bot automatically creates config.json the first time /setup is used.
This file stores:

Server name
Trap channel ID
Log channel ID
Timeout duration
Punishment type (timeout or ban)

You do not need to edit this file manually.

Commands


CommandDescriptionRequired Permission/setupConfigure trap channel, log channel, punishment & timeoutAdministrator/removeCompletely remove the trap from the serverAdministrator
/setup Options

trap_channel → Leave empty to auto-create #bot-trap
log_channel → Leave empty to auto-create private #timeout-logs
punishment → Choose Timeout or Ban
timeout_days → 1–28 days (only used when Timeout is selected)


How the Trap Works

User sends a message in the trap channel
Message is deleted
User is timed out or banned (depending on settings)
A detailed log is sent to the log channel
User’s recent messages are purged from other channels

The bot owner is fully exempt and only receives a friendly reply.

Notes

Settings are saved permanently and survive restarts
Each server has its own independent configuration
The log channel is private by default when auto-created


License
This project is proprietary.
All rights reserved. Unauthorized copying, modification, distribution, or use of this code is strictly prohibited.

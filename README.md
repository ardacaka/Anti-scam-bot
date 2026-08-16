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

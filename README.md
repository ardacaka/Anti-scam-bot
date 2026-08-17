# Anti-Scam Trap Bot

A Discord bot that automatically timeouts or bans users who post messages in designated “trap” channels. Perfect for catching scammers, spammers, or rule-breakers.

---

## Features

- Automatically **timeouts** or **bans** users who message in a trap channel
- Customizable timeout duration (1–28 days)
- Choice between **Timeout** or **Ban** as the punishment
- Option to **DM a permanent invite** to banned users **before** they are banned
- Auto-creates `#bot-trap` and a private `#timeout-logs` channel if none are selected
- Private log channel (only visible to Administrators, Moderators, and the bot)
- Deletes the offending message instantly
- Purges the user’s recent messages from other channels
- **Local Owners** – Admins can make specific users exempt from the trap (per server only)
- Saves all settings per server in `config.json` (including the permanent invite link)
- Replies with available commands + invite link when pinged
- Both the bot’s reply and the original ping message are automatically deleted after 30 seconds
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
```

---

## Setup Instructions

### 1. Download the files

Clone or download this repository.

### 2. Create a `.env` file

In the same folder as `Bot.py`, create a file named `.env` and put this inside:

```
DISCORD_TOKEN=your_discord_bot_token_here
```

Example:

```
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GaBcDe.FgHiJkLmNoPqRsTuVwXyZ1234567890
```

> Never upload the `.env` file to GitHub. It is already ignored by `.gitignore`.

### 3. Invite the bot

Give the bot these permissions:

- Moderate Members
- Ban Members
- Manage Messages
- Manage Channels
- Create Instant Invite
- Send Messages
- Embed Links
- View Channels

Administrator permission is recommended.

### 4. Run the bot

```bash
python Bot.py
```

---

## Configuration File

The bot automatically creates `config.json` the first time `/setup` is used.

This file stores:

- Server name
- Trap channel ID
- Log channel ID
- Timeout duration
- Punishment type (`timeout` or `ban`)
- Whether to send invite on ban
- Permanent invite link (if enabled)
- Local owners list

You do **not** need to edit this file manually.

---

## Commands

| Command          | Description                                      | Required Permission |
|------------------|--------------------------------------------------|---------------------|
| `/setup`         | Configure trap channel, log channel, punishment, timeout & invite option | Administrator |
| `/remove`        | Completely remove the trap from the server       | Administrator      |
| `/addowner`      | Add a local owner (exempt from the trap in this server only) | Administrator |
| `/removeowner`   | Remove a local owner from this server            | Administrator      |

### `/setup` Options

- `trap_channel` → Leave empty to auto-create `#bot-trap`
- `log_channel` → Leave empty to auto-create private `#timeout-logs`
- `punishment` → Choose **Timeout** or **Ban**
- `timeout_days` → 1–28 days (only used when Timeout is selected)
- `send_invite_on_ban` → Yes / No (DMs a permanent invite **before** banning the user)

---

## Local Owners

You can make specific users immune to the trap **only in the current server**:

- `/addowner @user` → Makes the user exempt in this server
- `/removeowner @user` → Removes the exemption

Local owners only work in the server they were added to.

---

## How the Trap Works

1. User sends a message in the trap channel
2. Message is deleted
3. If Ban + Invite option is enabled → Bot DMs the user a permanent invite **first**
4. User is timed out or banned
5. A detailed log is sent to the log channel
6. User’s recent messages are purged from other channels

---

## Notes

- Settings are saved permanently and survive restarts
- Each server has its own independent configuration
- The log channel is private by default when auto-created
- When the bot is pinged, both the reply and the original ping message are deleted after 30 seconds
- DMing may fail if the user has DMs closed (this is normal)

---

## License

This project is proprietary.  
All rights reserved. Unauthorized copying, modification, distribution, or use of this code is strictly prohibited.

---

**Original bot by [ardacaka](https://github.com/ardacaka/Anti-scam-bot)**
```

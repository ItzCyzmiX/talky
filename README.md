# talky

A Discord bot that lets you spin up isolated, persistent AI chatbot personas — each one living in its own channel with its own memory and admins.  

## How It Works

Running `/talk <bot_name>` creates a brand new text channel under a dedicated category (`BOT_CATEGORY_ID`, configured in `bot/consts.py`). That channel *is* the chatbot — everything sent inside it is treated as a conversation with `<bot_name>`, and the bot replies using Groq's LLM API.

**Per-channel state, not global state.** Each chatbot channel is backed by its own row in Supabase:

| Field | Purpose |
|---|---|
| `id` | The Discord channel ID — ties the row to the channel 1:1 |
| `admins` | List of user IDs allowed to manage this specific chatbot |
| `messages` | A JSON blob holding the full message history for that channel |

Because history is stored per-channel rather than per-user or globally, every chatbot persona keeps its own separate memory and can reference specific users who've spoken in that channel — conversations don't bleed into each other across different bot channels.

**Admin model.** Whoever runs `/talk` to create a channel is automatically its admin. Admins can:
- Promote other users with `/admin <user>` (adds them to that channel's `admins` list in Supabase)
- Tear the whole thing down with `/kill` — deletes both the Discord channel and its Supabase row. `/kill` only works if you're an admin of *that* channel; ordinary members can't nuke someone else's chatbot.
- `/status` just tells you whether you're currently an admin of the channel you're in.

**AI completions.** All chat replies go through Groq. The bot pulls the channel's stored `messages` history to give the model context, and can reference/attribute things to specific users in the conversation rather than treating it as one anonymous stream.

## Commands

| Command | Description |
|---|---|
| `/talk <bot_name>` | Creates a new chatbot channel under the configured category |
| `/help` | Lists all available commands |
| `/status` | Shows whether you're an admin in the current channel |
| `/admin <user>` | Grants the given user admin rights on the current chatbot channel (admin-only) |
| `/kill` | Deletes the current chatbot channel and its data (admin-only) |

## Setup

### 1. Prerequisites

- Python 3.10+
- A Discord bot application ([Discord Developer Portal](https://discord.com/developers/applications)) with the `applications.commands` and `bot` scopes, and the **Manage Channels** permission (needed to create/delete chatbot channels)
- A Groq API key ([console.groq.com](https://console.groq.com/))
- A Giphy API key ([developers.giphy.com](https://developers.giphy.com/))
- A Supabase project ([supabase.com](https://supabase.com/))

### 2. Clone and install

```bash
git clone https://github.com/ItzCyzmiX/talky.git
cd talky
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up Supabase

Create a table (e.g. `chatbots`) with:

| column | type |
|---|---|
| `id` | text/int8 (Discord channel ID) |
| `admins` | text[] (array of user IDs) |
| `messages` | jsonb (array of message objects) |

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_discord_bot_token
GROQ_API_KEY=your_groq_api_key
GIPHY_KEY=your_giphy_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_or_anon_key
```

### 5. Set your category ID

In `bot/consts.py`, set `BOT_CATEGORY_ID` to the Discord category ID under which new chatbot channels should be created. (Enable Developer Mode in Discord, right-click the category, "Copy ID".)

### 6. Run it

```bash
python main.py
```

Invite the bot to your server with the `bot` + `applications.commands` scopes, then run `/talk <bot_name>` in any channel to spin up your first chatbot.
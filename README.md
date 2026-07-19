# 🤖 Talky

A Discord bot that lets you create isolated, persistent AI chatbot personas — each one living in its own channel with its own memory, admin controls, and flexible LLM selection. Chat with anyone, anytime, powered by your choice of AI models.

---

## ✨ Features

### 💬 **Isolated Chatbot Channels**
- Create dedicated channels for AI personas using `/talk <bot_name>`
- Each channel has its own persistent memory and conversation history
- AI understands context and can reference specific users by their Discord names

### 🔒 **Private & Public Conversations**
- Create **public** channels (anyone in the server can see & chat)
- Create **private** channels (only invited members can access)
- Admins can add members with `/add <user>` or remove them with `/kick <user>`
- Perfect for private group discussions with AI

### 🧠 **Flexible AI Model Selection**
- **Default**: Llama 3.3 70B (via Groq) — fast, reliable, and free
- **Custom Models**: Choose from 24+ OpenRouter models with `/gpt`
- Automatic fallback to Llama if your selected model fails
- Models are cached on startup for quick switching

### 👑 **Admin Management**
- Channel creator is automatically an admin
- Promote other users to admin with `/admin <user>`
- Only admins can:
  - Add/kick users from private chats
  - Change the AI model with `/gpt`
  - Delete the channel with `/kill`

### 💾 **Persistent Memory**
- Last 30 messages stored per channel (configurable)
- Full conversation history in Supabase
- AI has context from previous messages in that channel
- Survives bot restarts

---

## 📋 How It Works

### Architecture

**Per-channel state, not global state.** Each chatbot channel is backed by its own row in Supabase:

| Field | Type | Purpose |
|---|---|---|
| `id` | int | Discord channel ID (1:1 mapping) |
| `admins` | int[] | User IDs with admin permissions |
| `messages` | jsonb | Full message history for the channel |
| `model` | text | Selected AI model (defaults to "llama") |
| `bot_name` | text | Name of the chatbot persona |

### Message Flow

1. User sends a message in a chatbot channel
2. Bot retrieves the channel's message history from Supabase
3. Bot formats messages with usernames: `(username) message content`
4. Selected AI model generates a response with full context
5. Response is saved to Supabase and sent to Discord
6. If a custom model fails, automatically reverts to Llama

---

## 🛠️ Commands

| Command | Arguments | Description | Permissions |
|---------|-----------|-------------|-------------|
| `/talk` | `<bot_name>` `[private]` | Create a new chatbot channel | Anyone (in creation channel) |
| `/help` | — | Show all available commands | Anyone (in creation channel) |
| `/status` | — | Check if you're an admin in current channel | Anyone |
| `/admin` | `<user>` | Promote a user to admin | Admin only |
| `/gpt` | — | Select AI model for this channel | Admin only |
| `/add` | `<user>` | Add user to private chat | Admin only |
| `/kick` | `<user>` | Remove user from private chat | Admin only |
| `/kill` | — | Delete the chatbot channel permanently | Admin only |

### Command Examples

```
# Create a public chat with ChatGPT persona
/talk bot_name: ChatGPT private: false

# Create a private group chat
/talk bot_name: SecretBot private: true

# Add a friend to your private chat
/add user: @JohnDoe

# Switch to a different AI model
/gpt → Select from 24+ options

# Promote someone to admin
/admin user: @Manager

# Remove someone from private chat
/kick user: @SpamBot

# Delete the entire channel and data
/kill
```

---

## 🚀 Setup Guide

### 1. Prerequisites

- **Python 3.10+**
- **Discord bot** with these permissions:
  - `bot` scope
  - `applications.commands` scope
  - Permissions: **Manage Channels**, **Send Messages**, **Embed Links**
  - ([Create at Discord Developer Portal](https://discord.com/developers/applications))
- **Groq API key** ([console.groq.com](https://console.groq.com/))
- **OpenRouter API key** for model selection ([openrouter.ai](https://openrouter.ai))
- **Giphy API key** for bot GIFs ([developers.giphy.com](https://developers.giphy.com/))
- **Supabase project** ([supabase.com](https://supabase.com/))

### 2. Clone & Install

```bash
git clone https://github.com/ItzCyzmiX/talky.git
cd talky

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up Supabase

Create a table named `chats` with these columns:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | bigint | ✅ | Discord channel ID (primary key) |
| `admins` | text[] | ✅ | Array of user ID strings |
| `bot_name` | text | ✅ | Name of the chatbot |
| `messages` | jsonb | ✅ | Message history JSON |
| `model` | text | ✅ | Selected AI model (defaults to "llama") |

**Example SQL:**
```sql
CREATE TABLE chats (
  id BIGINT PRIMARY KEY,
  admins TEXT[],
  bot_name TEXT,
  messages JSONB,
  model TEXT DEFAULT 'llama'
);
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token

# AI Models
GROQ_API_KEY=your_groq_api_key
OPENROUTER_KEY=your_openrouter_api_key

# Media
GIPHY_KEY=your_giphy_api_key

# Database
SUPABASE_URL=your_supabase_project_url
SUPABASE_SECRET_KEY=your_supabase_service_role_key
```

### 5. Configure Constants

Edit `bot/consts.py` and set your Discord IDs:

```python
import discord

# Your Discord server ID
GUILD = discord.Object(id=YOUR_GUILD_ID)

# Category where chatbot channels are created
BOTS_CATEGORY_ID = YOUR_CATEGORY_ID

# Channel where /talk command can be used (e.g., #bot-creation)
BOT_CREATION_CHANNEL = YOUR_CHANNEL_ID

# Optional customization
DESCRITPTION = "Bot to talk to ai characters!"
DELETE_DELAY = 15  # Seconds before ephemeral messages disappear
MESSAGE_HISTOY_LIMIT = 30  # Last N messages kept in memory
```

**How to find your IDs:**
1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click on server/category/channel → "Copy Server/Channel ID"

### 6. Run the Bot

```bash
python main.py
```

You should see:
```
We have logged in as YourBotName#0000
```

### 7. Invite to Your Server

Use this URL (replace `YOUR_CLIENT_ID`):
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=16777216&scope=bot%20applications.commands
```

Or manually:
1. Go to [Developer Portal](https://discord.com/developers/applications) → Your App → OAuth2 → URL Generator
2. Select scopes: `bot`, `applications.commands`
3. Select permissions: `Manage Channels`, `Send Messages`, `Embed Links`
4. Copy the generated URL and open in browser

---

## 📚 Example Workflows

### Workflow 1: Group Brainstorm
```
Admin: /talk bot_name: Brainstorm private: true
Admin: /add user: @TeamMember1
Admin: /add user: @TeamMember2
Everyone: Chat with the AI in the private channel
Admin: /gpt → Select a creative model like "Mistral Large"
Admin: /kill → Delete when done
```

### Workflow 2: Public Learning Channel
```
Teacher: /talk bot_name: Python-Tutor private: false
Teacher: /admin user: @Student1
Students: Ask questions, get AI-powered explanations
Teacher: /gpt → Switch between models for different explanations
Teacher: /kill → Archive the conversation later
```

### Workflow 3: Switching AI Models
```
/talk bot_name: MultiBot private: false
(Users chat with Llama)
Admin: /gpt → Switch to "Mistral Large" for complex analysis
Admin: /gpt → Switch to "Dolphin Mixtral" for creative writing
(Auto-fallback to Llama if selected model fails)
```

---

## ⚙️ Advanced Configuration

### Changing Memory Limit

Edit `bot/consts.py`:
```python
MESSAGE_HISTOY_LIMIT = 50  # Increase to 50 recent messages
```

Larger values = more context but slower API calls.

### Adding More OpenRouter Models

Models are fetched from OpenRouter at bot startup. To customize:
- Edit the filter in `bot/character_api.py` lines 20-27
- Currently filters for free models; you can remove `min_price=0, max_price=0` to allow paid models

### Custom System Prompts

Edit `bot/utils.py`:
```python
def sys_message(bot_name: str):
    return {
        "role": "system",
        "content": f"You are {bot_name}. Your custom instructions here...",
    }
```

---

## 🔧 Troubleshooting

### Bot doesn't respond
- Check Discord channel IDs in `bot/consts.py`
- Verify Supabase connection with correct credentials
- Check bot has "Manage Channels" permission

### API Key errors
- Verify `.env` file is in project root
- Check for typos in `GROQ_API_KEY`, `OPENROUTER_KEY`, `SUPABASE_SECRET_KEY`
- Ensure keys haven't expired or been revoked

### Model selection not working
- Check OpenRouter API key is valid
- Verify internet connection (models are fetched on startup)
- Check `bot.openrouter_models` has entries: add `print(self.openrouter_models)` to `on_ready()`

### Private chat permissions failing
- Ensure bot has "Manage Channels" Discord permission
- Check user isn't already added/removed from channel

### Supabase connection fails
- Test credentials: `supabase.from_("chats").select("id").execute()`
- Verify table `chats` exists with correct columns
- Check network connectivity and firewall rules

---

## 📦 Dependencies

- **discord.py 2.7.1** — Discord bot framework
- **groq 0.18.0** — Groq API client (Llama models)
- **openrouter 0.11.44** — OpenRouter API client (24+ models)
- **python-dotenv 1.0.1** — Environment variable management
- **aiohttp 3.13.3** — Async HTTP (Giphy API)
- **supabase 2.27.2** — Database client

---

## 🤝 Contributing

Found a bug or have a feature idea? Feel free to open an issue or submit a PR!

---

## 📝 License

This project is open source and available under the MIT License.

---

## 🎯 Roadmap

- [ ] Conversation exports (JSON/PDF)
- [ ] Custom AI system prompts per channel
- [ ] Message reactions for model votes
- [ ] Rate limiting per user
- [ ] Web dashboard for management
- [ ] Multi-language support

---

## 💡 Tips & Tricks

**Tip 1:** Use `/gpt` to test different models on the same conversation
- Great for comparing creative vs analytical responses

**Tip 2:** Private chats are perfect for sensitive discussions
- Admins can kick users without awkward public notifications

**Tip 3:** Tag the channel name in bot responses
- Feature: `await message.channel.send(f"{message.channel.name}: {response}")`
- Helps in multi-chat scenarios

**Tip 4:** Use system prompts to set personality
- Edit `sys_message()` to make bots role-play specific personas

---

Made with ❤️ by ItzCyzmiX | [GitHub](https://github.com/ItzCyzmiX/talky)

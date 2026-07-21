# 🤖 Talky

A Discord bot that lets you create isolated, persistent AI chatbots — each one living in its own channel with its own memory, admin controls, and flexible LLM selection. Chat with anyone, anywhere, about anything.

---

## TEST SERVER!
a test server for talky, feel free to join and stress test it (poor talky) [JOIN](https://discord.gg/sVB2N7uJ)

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

### 🖼️ **Image & GIF Embed Integration**
- Upload images in your messages
- AI analyzes images and responds based on visual content
- Supports up to **4 images per message** (20MB total max)
- Uses **Qwen 3.6 27B vision model** for accurate image understanding
- Works seamlessly with text in the same message

### 🧠 **Flexible AI Model Selection**
- **Default**: Llama 3.3 70B (via Groq) — fast, reliable, and free
- **Vision Mode**: Automatic when images are detected (Qwen 3.6 27B)
- **Custom Models**: Choose from 24+ OpenRouter models with `/gpt`
- Automatic fallback to Llama if your selected model fails
- Models are cached for quick switching

### ✏️ **Edit & Delete Messages**
- Right-click on **any bot message** → "Delete AI message" or "Edit AI message"
- **Edit user messages** and AI will automatically regenerate responses with the updated context
- Changes are instantly reflected in the **conversation history and database**
- Works for both user and AI messages

### 👑 **Admin Management**
- Channel creator is automatically an admin
- Promote other users to admin with `/admin <user>`
- Only admins can:
  - Add/kick users from private chats
  - Change the AI model with `/gpt`
  - Delete the channel with `/kill`
  - Private the channel with `/private`

### 💾 **Persistent Memory**
- Last 100 messages stored per channel (configurable)
- Full conversation history in Supabase
- AI has context from previous messages in that channel
- Survives bot restarts

### 🎭 **Accurate Character Roleplay**
- AI stays in character — not an AI pretending, **actually becomes** the persona
- Speaks with authentic vocabulary, tone, and attitude
- Has opinions and personality, not generic "customer service energy"
- Naturally uses user names in conversation

---

## 📋 How It Works

### Architecture

**Per-channel state, not global state.** Each chatbot channel is backed by its own row in Supabase:

| Field | Type | Purpose |
|---|---|---|
| `id` | bigint | Discord channel ID (1:1 mapping) |
| `admins` | text[] | User IDs with admin permissions |
| `messages` | jsonb | Full message history with Discord message IDs |
| `gpt` | text | Selected AI model (defaults to "llama") |
| `bot_name` | text | Name of the chatbot persona |

### Message Flow

1. User sends a message in a chatbot channel (with or without images)
2. If images are attached, bot switches to **vision mode** automatically
3. Bot retrieves the channel's message history from in-memory cache
4. Bot formats messages with usernames and image URLs: `(username) message content` + images
5. Selected AI model (or vision model) generates a response with full context
6. Response is sent to Discord and saved to cache & database
7. If user edits/deletes → both Discord and database are updated
8. If a custom model fails → automatically reverts to Llama

### Image Processing

- Accepts **image attachments** (PNG, JPG, WebP, etc.)
- **Automatic model switching** to vision-capable Qwen model when images detected
- Images passed as **URLs to the API** (fast, no local storage needed)
- **Max 4 images per message**, **20MB total** to prevent API throttling
- Vision responses seamlessly integrated into conversation history

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
| `/private` | — | Turns public chat to private | Admin only |
| `/kick` | `<user>` | Remove user from private chat | Admin only |
| `/kill` | — | Delete the chatbot channel permanently | Admin only |

### Context Menu Commands (Right-Click)

| Command | Target | Description | Who Can Use |
|---------|--------|-------------|------------|
| **Delete AI message** | Bot response | Delete the AI's message from history and Discord | Anyone |
| **Edit AI message** | Bot response | Edit the AI's response via modal popup | Anyone |

---

## 🚀 Setup Guide

### 1. Prerequisites

- **Python 3.10+**
- **Discord bot** with these permissions:
  - `bot` scope
  - `applications.commands` scope
  - Permissions: **Manage Channels**, **Send Messages**, **Embed Links**
  - ([Create at Discord Developer Portal](https://discord.com/developers/applications))
- **Groq API key** ([console.groq.com](https://console.groq.com/)) — for Llama and vision models
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
| `id` | bigint | ❌ | Discord channel ID (primary key) |
| `admins` | text[] | ✅ | Array of user ID strings |
| `bot_name` | text | ✅ | Name of the chatbot |
| `messages` | jsonb | ✅ | Message history JSON (includes discord_message_id for each message) |
| `gpt` | text | ✅ | Selected AI model (defaults to "llama") |

**Example SQL:**
```sql
CREATE TABLE chats (
  id BIGINT PRIMARY KEY,
  admins TEXT[],
  bot_name TEXT,
  messages JSONB,
  gpt TEXT DEFAULT 'llama'
);
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token
GUILD_ID=your_discord_guild_id
BOTS_CATEGORY_ID=your_category_id
BOT_CREATION_CHANNEL_ID=your_channel_id

# AI Models
GROQ_API_KEY=your_groq_api_key
OPENROUTER_KEY=your_openrouter_api_key

# Media
GIPHY_KEY=your_giphy_api_key

# Database
SUPABASE_URL=your_supabase_project_url
SUPABASE_SECRET_KEY=your_supabase_service_role_key
```

**How to find Discord IDs:**
1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click on server/category/channel → "Copy Server/Channel ID"

### 5. Optional Configuration

Edit `bot/consts.py` to customize:

```python
DESCRITPTION = "Bot to talk to ai characters!"   # Bot description
DELETE_DELAY = 15                                # Seconds before ephemeral messages disappear
MESSAGE_HISTOY_LIMIT = 100                       # Last N messages kept in memory
```

### 6. Run the Bot

```bash
python main.py
```

You should see:
```
Talky started!
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

## 📦 Dependencies

- **discord.py 2.7.1** — Discord bot framework
- **groq 0.18.0** — Groq API client (Llama models + vision)
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

Made with ❤️ by ItzCyzmiX | [GitHub](https://github.com/ItzCyzmiX/talky)

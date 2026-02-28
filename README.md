# 🤖 PLATINUM Telegram Forward Bot

The most advanced message forwarding bot on Telegram with unlimited features!

## ✨ Features

### 🔄 Forward Management
- ✅ **Unlimited Forward Tasks** - Create as many forwarding tasks as you need
- ✅ **Forward Chat to Bots** - Forward messages to bot chats
- ✅ **Forward Bots to Bots** - Forward between bot accounts
- ✅ **Clone Source** - Clone entire chat history (unlimited file size)
- ✅ **Support Forward Topics** - Works with forum topics

### 🛠️ Advanced Filters
- ✅ **User Filter** - Filter by specific user IDs (whitelist/blacklist)
- ✅ **Keyword Filter** - Filter messages by keywords
- ✅ **Crypto Filters** - Special filters for crypto-related content
- ✅ **Duplicate/Delay Filters** - Prevent duplicate forwards and add delays
- ✅ **Cleaner Filter** - Remove links, usernames, hashtags automatically
- ✅ **Filters Clone** - Clone filter settings between tasks

### 📝 Content Processing
- ✅ **Add Header/Footer** - Customize messages with headers and footers
- ✅ **Convert Buttons to Text** - Extract inline keyboard buttons as text
- ✅ **Replace/Reformat Content** - Advanced text replacement
- ✅ **Remove Line by Keyword** - Remove specific lines containing keywords
- ✅ **Remove Line by Order** - Remove lines by their position
- ✅ **Max Time Edit** - Edit messages within time limit

### 🌍 Translation & Media
- ✅ **Translate Language** - Auto-translate to 20+ languages
- ✅ **Watermark** - Add text watermarks to photos
- ✅ **Replace Sticker** - Replace stickers with custom ones

### ⏰ Scheduling
- ✅ **Auto Post Scheduler** - Schedule messages to post automatically
- ✅ **Power On/Off Schedule** - Automatically enable/disable tasks at set times
- ✅ **Schedule Power On/Off** - Multiple schedule options

### 👥 Management
- ✅ **Unlimited Manage Setup** - Full management capabilities
- ✅ **Dedicated Server** - Optimized for dedicated hosting
- ✅ **Blacklist/Whitelist Advanced** - Advanced user management

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8 or higher
- A Telegram Bot Token (from @BotFather)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure the Bot

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your bot token:
```
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_telegram_user_id
```

Get your bot token from [@BotFather](https://t.me/BotFather)
Get your user ID from [@userinfobot](https://t.me/userinfobot)

### Step 3: Run the Bot

```bash
python main.py
```

## 📖 Commands Reference

### 🔄 Forward Management
| Command | Description |
|---------|-------------|
| `/newtask` | Create a new forward task |
| `/mytasks` | List all your forward tasks |
| `/edittask [task_id]` | Edit an existing task |
| `/deletetask [task_id]` | Delete a forward task |
| `/enabletask [task_id]` | Enable a task |
| `/disabletask [task_id]` | Disable a task |

### 🛠️ Filters
| Command | Description |
|---------|-------------|
| `/addfilter [task_id] [type] [value]` | Add filter to task |
| `/removefilter [filter_id]` | Remove a filter |
| `/filters [task_id]` | View active filters |

### ⚙️ Settings
| Command | Description |
|---------|-------------|
| `/setdelay [task_id] [seconds]` | Set forwarding delay |
| `/setheader [task_id] [text]` | Add header to messages |
| `/setfooter [task_id] [text]` | Add footer to messages |
| `/setwatermark [task_id] [text] [position]` | Add watermark |
| `/settranslate [task_id] [lang_code]` | Enable translation |
| `/setschedule [task_id] on/off [HH:MM]` | Schedule power on/off |

### 🧹 Content Processing
| Command | Description |
|---------|-------------|
| `/clean [task_id] [options]` | Clean message content |
| `/replace [task_id] [old] [new]` | Replace text |
| `/removebykeyword [task_id] [keywords]` | Remove lines by keyword |
| `/removebyline [task_id] [line_numbers]` | Remove lines by order |

### 📊 Admin
| Command | Description |
|---------|-------------|
| `/stats` | View bot statistics |
| `/broadcast [message]` | Broadcast to all users |
| `/users` | List all users |

## 🎯 How to Create a Forward Task

1. **Start the bot**: Send `/start`
2. **Create task**: Send `/newtask`
3. **Select source**: Forward a message from the source chat
4. **Select destination**: Forward a message from the destination chat
5. **Enable task**: Use `/enabletask [task_id]` to start forwarding

## 🔧 Advanced Configuration

### Supported Languages for Translation
- English (en), Spanish (es), French (fr)
- German (de), Italian (it), Portuguese (pt)
- Russian (ru), Japanese (ja), Korean (ko)
- Chinese (zh), Arabic (ar), Hindi (hi)
- Turkish (tr), Polish (pl), Dutch (nl)
- Indonesian (id), Vietnamese (vi), Thai (th)
- Persian (fa), Urdu (ur)

### Watermark Positions
- `bottom-right` (default)
- `bottom-left`
- `top-right`
- `top-left`
- `center`

### Filter Types
- **keyword**: Filter by keywords in message text
- **user**: Filter by user IDs
- **crypto**: Special crypto content filter

## 📝 Example Usage

### Create a task with keyword filter
```
/newtask
[Forward source message]
[Forward destination message]
/addfilter 1 keyword bitcoin,ethereum
/enabletask 1
```

### Add watermark and translation
```
/setwatermark 1 "@MyChannel" bottom-right
/settranslate 1 es
```

### Schedule power on/off
```
/setschedule 1 on 08:00
/setschedule 1 off 22:00
```

## ⚠️ Important Notes

1. **Bot must be admin** in both source and destination chats to forward messages
2. **Privacy mode** must be disabled for the bot to see all messages
3. **Rate limits** apply - avoid setting very low delays
4. **Duplicate detection** is enabled by default to prevent spam

## 🔒 Security

- Admin commands are restricted to configured admin IDs
- User data is stored locally in SQLite database
- No external data sharing

## 🐛 Troubleshooting

### Bot not forwarding messages?
- Make sure the bot is an admin in both chats
- Check if the task is enabled (`/mytasks`)
- Verify filters aren't blocking messages

### Translation not working?
- Check internet connection
- Verify language code is supported

### Watermark not appearing?
- Ensure the task has watermark text set
- Check if the message contains a photo

## 📞 Support

For support and updates, contact the admin or check the bot's status with `/stats`.

## 📄 License

This project is for educational purposes. Use responsibly and in accordance with Telegram's Terms of Service.

---

**Made with ❤️ for the Telegram community**

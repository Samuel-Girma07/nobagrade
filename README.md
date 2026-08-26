# Telegram API Key Credit Checker Bot

An asynchronous Telegram bot built with [aiogram 3](https://docs.aiogram.dev/) and SQLite that allows users to submit their API key / identifier to request remaining credits. The request is forwarded to the administrator, who can reply with the balance to instantly deliver it back to the user.

---

## 🌟 Features

- **Interactive Menu**: Users can start with `/start` and click **💳 Check Remaining Credit** to submit their API key.
- **Direct Admin Forwarding**: Submissions are instantly formatted and forwarded to the administrator (`ADMIN_ID`).
- **Native Swipe-to-Reply**: The admin can simply **swipe & reply** directly to the notification message with the credit amount (e.g., `$24.50 remaining` or `1,500 credits`).
- **Direct Delivery**: The admin's reply is automatically routed and sent to the original requesting user with a formatted receipt.
- **Persistent SQLite Storage**: Tracks all requests, timestamps, states (`pending`, `replied`), and user history across bot restarts.
- **Admin Management Commands**:
  - `/pending` — View all pending requests awaiting review.
  - `/stats` — View total, pending, and answered request metrics.
  - `/reply <request_id> <credit>` — Manual fallback reply command.
  - `/admin` — Show admin help guide.
- **User History**: Users can view their recent checks and balances using **📜 My Recent Checks**.

---

## 📁 Project Structure

```
nobabot/
├── .env                  # Bot Token & Admin ID configuration
├── .env.example          # Environment template
├── config.py             # Config loader & validations
├── database.py           # Async SQLite database layer
├── handlers/
│   ├── __init__.py
│   ├── admin.py          # Admin reply & management handlers
│   ├── states.py         # FSM states for user inputs
│   └── user.py           # User commands, buttons, and submissions
├── keyboards/
│   ├── __init__.py
│   └── user_kb.py        # Inline keyboards for navigation
├── main.py               # Main entry point & polling loop
├── requirements.txt      # Dependencies
└── run.bat               # Windows batch runner
```

---

## 🚀 How to Run

### 1. Requirements
- Python 3.10+ installed

### 2. Setup & Virtual Environment (Already configured)
If setting up on a new machine:
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 3. Configuration (`.env`)
Make sure your `.env` contains:
```env
BOT_TOKEN=8919615961:AAH-WgjCJA01CTvx39hPEZIwruIax0Yi4k8
ADMIN_ID=494789813
```

### 4. Start the Bot
Run either:
```bash
.venv\Scripts\python main.py
```
or double-click `run.bat`.

---

## 📋 How It Works

1. **User interaction:**
   - User types `/start` and clicks **💳 Check Remaining Credit**.
   - User sends their API key or key identifier.
   - The bot acknowledges the submission and gives them a Request ID.

2. **Admin interaction:**
   - The admin receives a notification with the user's name, user ID, timestamp, and API key.
   - The admin **swipes to reply** to that message and types the remaining credit (e.g., `$12.00`).
   - The bot receives the reply, updates the database, confirms delivery to the admin, and messages the user with their credit update.

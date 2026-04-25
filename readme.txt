=========================================================
NZDUSD Automated Trading Bot (EA) - Setup Guide
=========================================================

Welcome to the NZDUSD Automated Trading Bot! This package contains everything you need to run the bot right away. It includes an automated setup process, so you do not need to configure complex environments.

---------------------------------------------------------
1. INITIAL SETUP
---------------------------------------------------------
Before running the bot, you need to set up your configuration file:

1. Look for the file named "config.json.sample" in this folder.
2. Make a copy of it and rename the copy to "config.json" (or just rename the existing file).
3. Open "config.json" in a text editor (like Notepad).
4. You will see various trading parameters (like Risk, Stop Loss, etc.). You can adjust these if you know what you are doing, or leave the defaults.
5. Pay special attention to the Telegram settings at the bottom (see Section 2 below).

---------------------------------------------------------
2. SETTING UP TELEGRAM NOTIFICATIONS (Optional but Recommended)
---------------------------------------------------------
The bot can send live trade alerts and status updates directly to your Telegram app.

Step A: Create the Telegram Bot
1. Open the Telegram app and search for the user "@BotFather" (it has a blue checkmark).
2. Start a chat and send the command: /newbot
3. Follow the prompts to give your bot a Name and a Username (username must end in "bot").
4. BotFather will reply with an "HTTP API Token" (a long string of letters and numbers).
5. Copy this Token and paste it into your config.json file next to "TELEGRAM_BOT_TOKEN".

Step B: Get Your Chat ID
1. In Telegram, search for the user "@userinfobot" or "@RawDataBot".
2. Start a chat with it. It will instantly reply with your account details.
3. Look for the line that says "Id:" (a string of numbers like 123456789).
4. Copy this Number and paste it into your config.json file next to "TELEGRAM_CHAT_ID".

Step C: Activate the Bot
1. Search for the bot you created in Step A by its Username.
2. Click on it and press the "Start" button at the bottom so it has permission to message you.

Your config.json should look like this at the bottom:
    "TELEGRAM_BOT_TOKEN": "123456789:ABCdefGHIjklmNOPqrstUVwXyz",
    "TELEGRAM_CHAT_ID": "123456789"

---------------------------------------------------------
3. RUNNING THE BOT
---------------------------------------------------------
Once your config.json is saved, you are ready to start:

1. Double-click the "Start_EA.bat" file.
2. A command prompt window will open. It will automatically handle the environment setup and launch the bot.
3. Keep this window open while you want the bot to trade. If you close the window, the bot will stop.
4. You should see log messages indicating that the bot has started successfully and is monitoring the market. If you set up Telegram, you should also receive a startup notification there!

---------------------------------------------------------
4. TROUBLESHOOTING
---------------------------------------------------------
- "File not found: config.json": Make sure you renamed config.json.sample to config.json.
- No Telegram messages: Double-check your Token and Chat ID for typos. Ensure you pressed "Start" in the chat with your own bot.
- Bot window closes immediately: Right-click inside the folder, select "Open in Terminal" (or open Command Prompt here), type "Start_EA.bat" and press Enter. This will let you see the error message before the window disappears.

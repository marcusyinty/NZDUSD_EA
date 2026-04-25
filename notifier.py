import requests
import logging

class TelegramNotifier:
    def __init__(self, config):
        self.bot_token = config.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = config.get("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)

    def send_message(self, message):
        """
        Sends a Markdown formatted message to Telegram.
        Outbound only, robust to network errors.
        """
        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            # Short timeout to prevent blocking the main loop
            response = requests.post(url, json=payload, timeout=3)
            if response.status_code != 200:
                logging.error(f"Telegram API Error: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Telegram network error: {e}")

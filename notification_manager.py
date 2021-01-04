from color_print import ColorPrint
from snc_config import SncConfig
from telegram_sender import TelegramSender
from email_sender import EmailSender


class NotificationManager:
    def __init__(self, notification_provider, email_recipient, telegram_chat_id):
        ColorPrint.info("Init: NotificationManager")
        self.config = SncConfig()
        if notification_provider and email_recipient and telegram_chat_id:
            self.provider = notification_provider
            self.recipient = email_recipient
            self.chat_id = telegram_chat_id
            self.notify = True
        else:
            self.provider = self.config.getstring('notification', 'notification_provider')
            self.recipient = self.config.getstring('notification', 'notification_email_recipient')
            self.chat_id = self.config.getstring('notification', 'notification_telegram_chat_id')
            self.notify = self.config.getboolean('notification', 'notify')

    def send_notification(self, status, subject,  message):
        ColorPrint.info("Send message {0}".format(message))
        list_of_providers = self.provider.split(",")
        if len(list_of_providers) == 0 or not self.notify:
            ColorPrint.err("Notification providers list is empty or notification disabled.")
        else:
            for provider in list_of_providers:
                if status is True:
                    subject += " Successful"
                else:
                    subject += ' Failed'

                if provider == "telegram":
                    ColorPrint.info("Send telegram message")
                    telegram = TelegramSender(None)
                    telegram.send_message(self.chat_id, subject + '\n\n' + message)
                if provider == "email":
                    ColorPrint.info("Send email message")
                    email_sender = EmailSender(None, None, None, None)
                    email_sender.send_message(self.recipient, subject, message, status)

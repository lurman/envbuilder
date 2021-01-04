import requests


class TelegramSender:

    def __init__(self, token):
        if token:
            self.token = token
        else:
            self.token = '996719894:AAE4iUm34oRxEQ5OQ644GIgDZJbh3169tPw'
        self.base_url = 'https://api.telegram.org/bot' + self.token + "/"

    def send_message(self, chat_id, message):
        url = self.base_url + 'sendMessage?chat_id=' + chat_id + '&parse_mode=Markdown&text=' + message
        response = requests.get(url)
        return response.json()

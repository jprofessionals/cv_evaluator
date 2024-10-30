import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

global client
global check_cv_func

def handle_message_events(message, say):
    text = message['text']
    user = client.users_info(user=message['user'])
    email = user['user']['profile']['email']
    name = user['user']['profile']['real_name']
    match text:
        case "sjekk":
            say(text=f"OK, vent mens jeg sjekker din CV {name}")
            result = check_cv_func(email)
            if result != "ok":
                say(text=f"Beklager {name}, epost {email} er ukjent hos cvparner")
        case _:
            say(text=f"Beklager {name}, foreløpig kan jeg bare kommandoen \"sjekk\"")

class MySlack:
    cv_evaluate_header = "Hei {}! Jeg har sett over CV'n din og har følgende ting å si om den: "
    def __init__(self, slack_bot_token, slack_app_token, slack_signing_secret, check_cv_func_arg, logger):
        assert slack_bot_token and slack_app_token and slack_signing_secret
        self.slack_signing_secret = slack_signing_secret
        self.slack_app_token = slack_app_token
        self.slack_bot_token = slack_bot_token
        self.app = App(token=self.slack_bot_token, signing_secret=self.slack_signing_secret)
        self.app.event("message")(handle_message_events)
        self.logger = logger
        logging.getLogger('slack_bolt.App').setLevel(logging.WARN)
        global client
        client = WebClient(token=self.slack_bot_token)
        global check_cv_func
        check_cv_func = check_cv_func_arg

    def send_message(self, email, text):
        global client
        client = WebClient(token=self.slack_bot_token)

        try:
            resp = client.users_list(limit=200)
            self.logger.debug(f"got {len(resp['members'])} users:")
            name = ""
            slack_id = ""
            for m in resp['members']:
                if m['profile'] and 'email' in m['profile']:
                    member_email = m['profile']['email']
                    if email != member_email:
                        continue
                else:
                    continue
                name = m['real_name']
                slack_id = m['id']
            header = self.cv_evaluate_header.format(name)
            response = client.chat_postMessage(channel=slack_id, text=f"{header}{text}")
        except SlackApiError as e:
           # You will get a SlackApiError if "ok" is False
           assert e.response["ok"] is False
           assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
           print(f"Got an error: {e.response['error']}")
           # Also receive a corresponding status_code
           print(e)
           assert isinstance(e.response.status_code, int)
           print(f"Received a response status_code: {e.response.status_code}")


    def start_listen_mode(self):
        print("booting up")
        handler = SocketModeHandler(self.app, self.slack_app_token)
        handler.start()
        print("shutting down")
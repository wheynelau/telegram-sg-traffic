import requests
import requests.utils


class TrafficTelegramBot:
    """
    """
    base_API = f"https://api.telegram.org/bot"
    API_endpoints = {
        'send': "sendMessage",
        'edit': "editMessageText"
    }

    def __init__(self, botToken, chatID):
        """
        Params needed to create Bot object

        :param botToken: Token for telegram API
        :param chatID: chatID from channel or group
        """

        # Create base API with bot token

        self._baseEndpoint = TrafficTelegramBot.base_API + botToken + '/'
        self._chatID = chatID

        # Set default params with chat ID

        self.params = self._create_params()

    def update_channel(self, action: str, **kwargs):
        """
        Function for api calls
        :param action: currently only send, edit
        :param kwargs: check telegra
        :return:
        """
        try:
            url = self._baseEndpoint + TrafficTelegramBot.API_endpoints[action.lower()]
            self.params.update(kwargs)
            req = requests.get(url, params=self.params)
            if self._error_handling_api(req):
                print(f"Completed action {action}")

            else:
                print(f"Unable to complete {action}.Check error above")


        except KeyError as e:
            print(f"Invalid action {e}")

    def _create_params(self):
        """
        Creates default parameters with provided instance variable chat_ID
        :return: dict of parameters
        """
        params = {
            "chat_id": self._chatID,
            "parse_mode": "HTML"
        }
        return params

    @staticmethod
    def _error_handling_api(response: requests.models.Response):
        """
        Checks response URL for any error
        :param response: response object from requests.get function
        :return : Returns boolean True if successful call else False
        """
        ResJson = response.json()
        if not ResJson['ok']:
            print(ResJson['description'])
            return False
        else:
            return True

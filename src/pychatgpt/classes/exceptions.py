# Exceptions Class

class PyChatGPTException(Exception):
    def __init__(self, message):
        self.message = message


class Auth0Exception(PyChatGPTException):
    def __init__(self, message):
        self.message = message


class IPAddressRateLimitException(PyChatGPTException):
    def __init__(self, message):
        self.message = message


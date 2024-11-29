class Error(Exception):
    def __init__(self, message):
        super().__init__(message)


class AccountBanned(Exception):
    def __init__(self, message):
        super().__init__("Аккаунт заблокирован!")
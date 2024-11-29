from api.utools_api import uToolsAPIClient
from logic.classes import Account, Settings

from .api import get_id_by_auth_token
from .basic import add_message


async def validate_account(account: Account, worker_name:str=None):
    fields_to_check = {
        'proxy': "Нужно указать proxy!",
        'screen_name': "Нужно указать screen_name",
        'session': "Нужно указать session",
        'auth_token': "Нужно указать auth_token",
        'settings': "Необходимо указать settings"
    }

    for field, error_message in fields_to_check.items():
        value = getattr(account, field)
        if value is None or (isinstance(value, str) and value == ''):
            add_message(error_message, account.screen_name, account.color, "error", worker_name)
            return False
    
    if not isinstance(account.settings, Settings):
        add_message("settings должны быть объектом класса Settings", account.id, account.color, "error", worker_name)
        return False

    return True


async def validate_auth_token(utools_client: uToolsAPIClient, account: Account, worker_name:str=None):
    add_message(f"Валидация auth_token...", account.screen_name, account.color, "log", worker_name)
    try:
        if await get_id_by_auth_token(utools_client, account) == account.id:
            add_message("Валидация пройдена!", account.screen_name, account.color, "success", worker_name)
            return True
            
        add_message("Валидация провалена! Проверьте auth_token!", account.screen_name, account.color, "error", worker_name)
        await utools_client.close()
        return False
    except Exception as e:
        add_message(f"Ошибка при валидации auth_token: {e}", account.screen_name, account.color, "error", worker_name)
        await utools_client.close()
        return False
from api.twttr_api import TwttrAPIClient
from api.utools_api import uToolsAPIClient
from logic.classes import Account
from logic.exceptions import Error, AccountBanned
import asyncio

from .basic import add_message, send_telegram_message
from .data import (
    check_if_messages_in_conversation_from_response,
    get_dm_init_data_from_response,
    get_dm_list_data_from_response,
    get_maximal_entry_id,
    get_model_info_from_response,
    get_reposted_timeline_data_from_response,
    get_sorted_conversations,
    get_sorted_messages,
    get_tweet_data_from_response,
    get_inbox_conversations
)
from .database import add_or_update_user

async def handle_error(e: Exception, account: Account, worker_name: str = None):
    """Общая обработка ошибок."""
    error_message = str(e)
    if "This request looks like it might be automated" in error_message:
        account.soft_detected = True
        add_message(
            "⚠️ Автоматика была замечена.\n🕔 Ожидание",
            account.screen_name,
            type="warning"
        )
        send_telegram_message(
            f"⚠️ Автоматика была замечена.\n🕔 Ожидание {account.settings.if_detected_cooldown_seconds}с.",
            account.screen_name
        )
    if "spam" in error_message or "retricted" in error_message:
        send_telegram_message(f"🚨 АККАУНТ ЗАБЛОКИРОВАН! 🚨", account.screen_name)
        raise AccountBanned("Аккаунт заблокирован")
    if "Sender is not verified and their rate limit has been exceeded" in error_message:
        account.soft_detected = True
        send_telegram_message(f"🕔 Превышен лимит - кулдаун", account.screen_name)

    add_message(f"Ошибка: {error_message}", account.screen_name, account.color, "error", worker_name)

async def with_retries(func, max_retries=3, *args, **kwargs):
    """Обертка для вызова функции с повторными попытками."""
    try_number = 1
    while try_number <= max_retries:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if try_number == max_retries:
                raise
            try_number += 1
            await asyncio.sleep(3)

async def send_dm(twttr_client: TwttrAPIClient, account: Account, message: str, user_id: int = "", conversation_id: int = "", username: str = "", media_id: int = ""):
    async def send_message():
        response = await twttr_client.send_dm(
            message,
            to_user_id=user_id,
            conversation_id=conversation_id,
            to_user_name=username,
            media_id=media_id
        )
        add_message(f"Сообщение отправлено!", account.screen_name, account.color, "success")
        if user_id:
            await add_or_update_user(account, user_id=user_id)
        elif conversation_id:
            await add_or_update_user(account, user_id=conversation_id)
        return True

    try:
        return await with_retries(send_message)
    except Exception as e:
        await handle_error(e, account)
        return False

async def get_model_info(twttr_client: TwttrAPIClient, account: Account, worker_name: str = None):
    async def fetch_model_info():
        response = await twttr_client.get_user(account.screen_name)
        return await get_model_info_from_response(response)

    try:
        add_message("Получаю информацию об аккаунте модели...", account.screen_name, account.color, "log", worker_name)
        status, *data = await with_retries(fetch_model_info)
        if status:
            add_message("Информация о модели получена!", account.screen_name, account.color, "success", worker_name)
        else:
            add_message("Не удалось получить информацию о модели", account.screen_name, account.color, "error", worker_name)
        return status, *data
    except Exception as e:
        await handle_error(e, account, worker_name)
        return False, None, None, None, None, None


async def get_id_by_auth_token(utools_client: uToolsAPIClient, account: Account, worker_name: str = None):
    """Получение ID модели по auth_token с повторными попытками."""
    async def fetch_id():
        add_message(f"Получаю ID модели...", account.screen_name, account.color, "log", worker_name)
        response = await utools_client.get_user_id_by_auth_token()
        return int(response.get("data")) if response.get("data") else False

    try:
        return await with_retries(fetch_id)
    except Exception as e:
        await handle_error(e, account, worker_name)
        return False


async def get_ct0_by_auth_token(utools_client: uToolsAPIClient, account: Account, worker_name: str = None):
    """Получение ct0 по auth_token с повторными попытками."""
    async def fetch_ct0():
        add_message(f"Получаю ct0...", account.screen_name, account.color, "log", worker_name)
        response = await utools_client.get_ct0_by_auth_token()
        return response.get("data")

    try:
        return await with_retries(fetch_ct0)
    except Exception as e:
        await handle_error(e, account, worker_name)
        return False



async def init_dm(utools_client: uToolsAPIClient, twttr_client: TwttrAPIClient, account: Account, worker_name: str = None):
    """Инициализация DM с повторными попытками."""
    async def fetch_init_dm():
        add_message(f"Инициализация DM...", account.screen_name, account.color, "log", worker_name)
        response = await utools_client.get_dms_init()
        status, messages, conversations, users = await get_dm_init_data_from_response(twttr_client, account, response)

        if not status:
            add_message("Не удалось проинициализировать DM", account.screen_name, account.color, "error", worker_name)
            return False, None, [], [], []

        maximal_entry = await get_maximal_entry_id(conversations)
        conversations = await get_inbox_conversations(conversations)
        return True, maximal_entry, messages, conversations, users

    try:
        return await with_retries(fetch_init_dm)
    except Exception as e:
        await handle_error(e, account, worker_name)
        return False, None, [], [], []


async def get_dms(utools_client: uToolsAPIClient, twttr_client: TwttrAPIClient, account: Account, max_id: int = None, worker_name: str = None):
    """Получение списка DM с повторными попытками."""
    if not max_id:
        return None, [], [], []

    async def fetch_dms():
        add_message(f"Получаю список диалогов...", account.screen_name, account.color, "log", worker_name)
        response = await utools_client.get_dms_list(max_id)

        status, min_entry_id, messages, conversations, users = await get_dm_list_data_from_response(twttr_client, account, response, worker_name)

        if not status:
            add_message("Не удалось получить список DM", account.screen_name, account.color, "error", worker_name)
            return None, [], [], []

        messages = await get_sorted_messages(messages)
        conversations = await get_sorted_conversations(account, messages, conversations, worker_name)

        return min_entry_id, messages, conversations, users

    try:
        return await with_retries(fetch_dms)
    except Exception as e:
        await handle_error(e, account, worker_name)
        return None, [], [], []

    

async def retweet(twttr_client: TwttrAPIClient, account: Account, tweet_id: int):
    """Ретвит указанного твита."""
    async def perform_retweet():
        response = await twttr_client.retweet_tweet(tweet_id)
        add_message(f"Ретвит успешно выполнен!", account.screen_name, account.color, "success")
        return True

    try:
        return await with_retries(perform_retweet)
    except Exception as e:
        await handle_error(e, account, "")
        return None


async def unretweet(twttr_client: TwttrAPIClient, account: Account, tweet_id: int):
    """Отмена ретвита указанного твита."""
    async def perform_unretweet():
        response = await twttr_client.unretweet_tweet(tweet_id)
        add_message(f"Ретвит успешно отменен!", account.screen_name, account.color, "success")
        return True

    try:
        return await with_retries(perform_unretweet)
    except Exception as e:
        await handle_error(e, account, "")
        return None



async def tweet_info(twttr_client:TwttrAPIClient, account:Account, tweet_id:int, worker_name:str=None):
    async def fetch_tweet_info():
        response = await twttr_client.get_tweet_info(tweet_id)
        tw = await get_tweet_data_from_response(response)
        return tw
    
    try:
        return await with_retries(fetch_tweet_info)
    except Exception as e:
        await handle_error(e, account, worker_name)
        return None


async def ban(twttr_client:TwttrAPIClient, account:Account, user_id:int):
    async def perform_ban():
        add_message("Блокирую пользователя", account.screen_name, account.color, "error")
        response = await twttr_client.block_user(user_id)
        return True

    try:
        return await with_retries(perform_ban)
    except Exception as e:
        await handle_error(e, account, "")
        return None


async def get_reposted_timeline(twttr_client:TwttrAPIClient, account:Account, tweet_id:int, cursor:str=None, worker_name:str=None):
    async def fetch_reposted_timeline():
        response = await twttr_client.reposted_timeline(tweet_id, cursor)
        return await get_reposted_timeline_data_from_response(twttr_client, account, response, worker_name)
    
    try:
        return await with_retries(fetch_reposted_timeline)
    except Exception as e:
        await handle_error(e, account, worker_name)
        return None, []


async def check_if_messages_in_conversation(twttr_client:TwttrAPIClient, account:Account, user_id:int=None, worker_name:str=None):
    async def perform_check_if_messages_in_conversation():
        response = await twttr_client.get_dm_conversation(user_id)
        return await check_if_messages_in_conversation_from_response(response)
    
    try:
        return await with_retries(perform_check_if_messages_in_conversation)
    except Exception as e:
        await handle_error(e, account, worker_name)
        return False
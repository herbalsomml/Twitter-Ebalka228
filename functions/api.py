
from api.twttr_api import TwttrAPIClient
from api.utools_api import uToolsAPIClient
from logic.classes import Account
from logic.exceptions import Error, AccountBanned

from .basic import add_message, send_telegram_message
from .data import (check_if_messages_in_conversation_from_response,
                   get_dm_init_data_from_response,
                   get_dm_list_data_from_response, get_maximal_entry_id,
                   get_model_info_from_response,
                   get_reposted_timeline_data_from_response,
                   get_sorted_conversations, get_sorted_messages,
                   get_tweet_data_from_response)
from .database import add_or_update_user


async def check_automated(e: Error, account: Account, worker_name:str=None):
    if "This request looks like it might be automated" in str(e):
        account.soft_detected = True
        add_message("⚠️ Автоматика была замечена.\n🕔 Ожидание", account.screen_name, type="warning")
        send_telegram_message(f"⚠️ Автоматика была замечена.\n🕔 Ожидание {account.settings.if_detected_cooldown_seconds}с.", account.screen_name)


async def check_banned(e: Error, account: Account, worker_name:str=None):
    if "spam" in str(e) or "retricted" in str(e):
       # await add_message("🚨 АККАУНТ ЗАБЛОКИРОВАН! 🚨", account.screen_name, account.color, "error")
        send_telegram_message(f"🚨 АККАУНТ ЗАБЛОКИРОВАН! 🚨", account.screen_name)
        raise AccountBanned("Аккаунт заблокирован")


async def send_dm(twttr_client: TwttrAPIClient, account: Account, message:str, user_id:int="", username:str="", media_id:int=""):
    try:
        r = await twttr_client.send_dm(message, to_user_id=user_id, to_user_name=username, media_id=media_id)
        add_message(f"Сообщение отправлено!", account.screen_name, account.color, "success")
        await add_or_update_user(account, user_id)
        return True
    except Exception as e:
        add_message(f"Ошибка при отправке сообщения: {e}", account.screen_name, account.color, "error")
        await check_automated(e, account)
        await check_banned(e, account)
        return False


async def get_model_info(twttr_client: TwttrAPIClient, account: Account, worker_name:str=None):
    add_message(f"Получаю информацию об аккаунте модели...", account.screen_name, account.color, "log", worker_name)
    try:
        r = await twttr_client.get_user(account.screen_name)
        status, id, name, screen_name, followers_count, pinned_tweet_id = await get_model_info_from_response(r)
        if not status:
            add_message("Не удалось получить информацию о модели", account.screen_name, account.color, "error", worker_name)
            return False, None, None, None, None, None
        add_message("Информация о модели получена!", account.screen_name, account.color, "success", worker_name)
        return True, id, name, screen_name, followers_count, pinned_tweet_id
    except Exception as e:
        add_message(f"Ошибка при получении информации о модели: {e}", account.screen_name, account.color, "error", worker_name)
        await check_automated(e, account)
        await check_banned(e, account)
        return False, None, None, None, None, None


async def get_id_by_auth_token(utools_client: uToolsAPIClient, account: Account, worker_name:str=None):
    while True:
        try:
            add_message(f"Получаю ID модели...", account.screen_name, account.color, "log", worker_name)
            r = await utools_client.get_user_id_by_auth_token()
            return int(r.get("data")) if r.get("data") else False
        except Exception as e:
            add_message(f"Ошибка при получении ID по auth_token: {e}", account.screen_name, account.color, "error", worker_name)
            await check_automated(e, account)
            await check_banned(e, account)
            return False
    

async def get_ct0_by_auth_token(utools_client: uToolsAPIClient, account: Account, worker_name:str=None):
    try:
        add_message(f"Получаю ct0...", account.screen_name, account.color, "log", worker_name)
        r = await utools_client.get_ct0_by_auth_token()
        return r.get("data")
    except Exception as e:
        add_message(f"Ошибка при получении ct0: {e}", account.screen_name, account.color, "error", worker_name)
        await check_automated(e, account)
        await check_banned(e, account)
        return False


async def init_dm(utools_client:uToolsAPIClient, twttr_client:TwttrAPIClient, account: Account, worker_name:str=None):
    try:
        add_message(f"Инициализация DM...", account.screen_name, account.color, "log", worker_name)
        r = await utools_client.get_dms_init()
        status, messages, conversations, users = await get_dm_init_data_from_response(twttr_client, account, r)        

        if not status:
            add_message("Не удалось проинициализировать DM", account.screen_name, account.color, "error", worker_name)
            return False, None, [], [], []
        maximal_entry = await get_maximal_entry_id(conversations)
        return True, maximal_entry, messages, conversations, users
    except Exception as e:
        add_message(f"Ошибка при инициализации DM: {e}", account.screen_name, account.color, "error", worker_name)
        await check_automated(e, account)
        await check_banned(e, account)
        return False, None, [], [], []
    

async def get_dms(utools_client:uToolsAPIClient, twttr_client:TwttrAPIClient, account:Account, max_id:int=None, worker_name:str=None):
 #   try:
        if not max_id:
            return None, [], [], []
        add_message(f"Получаю список диалогов...", account.screen_name, account.color, "log", worker_name)
        r = await utools_client.get_dms_list(max_id)
        
        status, min_entry_id, messages, conversations, users = await get_dm_list_data_from_response(twttr_client, account, r, worker_name)

        if not status:
            add_message("Не удалось получить список DM", account.screen_name, account.color, "error", worker_name)
            return None, [], [], []
        
        messages = await get_sorted_messages(messages)
        conversations = await get_sorted_conversations(account, messages, conversations, worker_name)
        
        return min_entry_id, messages, conversations, users
 #   except Exception as e:
  #      add_message(f"Ошибка при получении списка DM: {e}", account.screen_name, account.color, "error", worker_name)
   #     await check_automated(e, account)
    #    await check_banned(e, account)
     #   return None, [], [], []
    

async def retweet(twttr_client:TwttrAPIClient, account:Account, tweet_id:int):
    try:
        r = await twttr_client.retweet_tweet(tweet_id)
        add_message(f"Ретвит успешно выполнен!", account.screen_name, account.color, "success")
    except Exception as e:
        add_message(f"Ошибка при ретвите: {e}", account.screen_name, account.color, "error")
        await check_automated(e, account)
        await check_banned(e, account)


async def unretweet(twttr_client:TwttrAPIClient, account:Account, tweet_id:int):
    try:
        r = await twttr_client.unretweet_tweet(tweet_id)
        add_message(f"Ретвит успешно отменен!", account.screen_name, account.color, "success")
    except Exception as e:
        add_message(f"Ошибка при отмене ретвита: {e}", account.screen_name, account.color, "error")
        await check_automated(e, account)
        await check_banned(e, account)


async def tweet_info(twttr_client:TwttrAPIClient, account:Account, tweet_id:int, worker_name:str=None):
    try:
        r = await twttr_client.get_tweet_info(tweet_id)
        tw = await get_tweet_data_from_response(r)
        return tw

    except Exception as e:
        add_message(f"Ошибка при получении информации о твите: {e}", account.screen_name, account.color, "error", worker_name)
        await check_automated(e, account)
        await check_banned(e, account)


async def ban(twttr_client:TwttrAPIClient, account:Account, user_id:int):
    try:
        add_message("Блокирую пользователя", account.screen_name, account.color, "error")
        await twttr_client.block_user(user_id)
    except Exception as e:
        add_message(f"Ошибка при бане пользователя: {e}", account.screen_name, account.color, "error")
        await check_automated(e, account)
        await check_banned(e, account)


async def get_reposted_timeline(twttr_client:TwttrAPIClient, account:Account, tweet_id:int, cursor:str=None, worker_name:str=None):
    try:
        r = await twttr_client.reposted_timeline(tweet_id, cursor)
        return await get_reposted_timeline_data_from_response(twttr_client, account, r, worker_name)
    except Exception as e:
        add_message(f"Ошибка при получении списка ретвитнувших: {e}", account.screen_name, account.color, "error", worker_name)
        await check_automated(e, account)
        await check_banned(e, account)


async def check_if_messages_in_conversation(twttr_client:TwttrAPIClient, account:Account, user_id:int=None, worker_name:str=None):
    try:
        r = await twttr_client.get_dm_conversation(user_id)
        return await check_if_messages_in_conversation_from_response(r)
    except Exception as e:
        add_message(f"Ошибка при проверке статуса диалога: {e}", account.screen_name, account.color, "error", worker_name)
        await check_automated(e, account)
        await check_banned(e, account)
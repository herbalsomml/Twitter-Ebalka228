import asyncio
import random

from api.twttr_api import TwttrAPIClient
from api.utools_api import uToolsAPIClient
from functions.api import get_ct0_by_auth_token, get_model_info, tweet_info
from functions.basic import add_message
from functions.data import check_if_model
from functions.database import (create_database_and_table,
                                create_shared_database, is_tweet_did)
from functions.validators import validate_auth_token
from logic.classes import Account, Tweet, User
from logic.constants import MANAGER_MESSAGE
from logic.exceptions import AccountBanned

from .api import ban, init_dm, retweet, send_dm, unretweet
from .basic import wait_delay
from .database import block_user, is_user_in_blacklist


async def initialize(twttr_client: TwttrAPIClient, utools_client: uToolsAPIClient, account: Account, worker_name:str=None):
    model_info_status, id , name, screen_name, followers_count, pinned_tweets = await get_model_info(twttr_client, account)
    if not model_info_status:
        return False
        
    account.id = id
    account.name = name
    account.screen_name = screen_name
    account.followers_count = followers_count
    account.pinned_tweets = pinned_tweets
    
    if not await validate_auth_token(utools_client, account):
        return False
    
    ct0 = await get_ct0_by_auth_token(utools_client, account)

    if not ct0:
        add_message("Не удалось получить ct0", account.screen_name, account.color, "error", worker_name)
        return False

    account.ct0 = ct0

    if not await create_shared_database(account):
        return False
    
    if not await create_database_and_table(account):
        return False
    
    return True


async def initialize_dm(utools_client:uToolsAPIClient, twttr_client:TwttrAPIClient, account:Account):
    status, maximal_entry, messages, conversations, users = await init_dm(utools_client, twttr_client, account)
    if not status:
        return False, None

    if not account.settings.work_with_inbox:
        return True, maximal_entry, [], [], []

    return True, maximal_entry, messages, conversations, users

async def check_user(user:User, account:Account):
    if user.id == account.id:
        return False

    if not user:
        return False
    
    if user.followers_count < account.settings.followers_to_work:
        return False
    
    if not user.is_blue_verified and not account.settings.work_with_not_blue_verified:
        return False
    
    if not account.settings.work_if_not_sure_that_its_model and not await check_if_model(user.description, user.urls):
        return False 
    
    if not user.can_dm:
        return False
    
    return True


async def check_user_for_critical(user, account):
    if not user:
        return False

    if user.blocking:
        return False

    if user.dm_blocking:
        return False
    
    return True

 
async def get_link_to_promote(twttr_client:TwttrAPIClient, account: Account, worker_name:str=None):
    add_message("Получаю ссылку для промоутинга", account.screen_name, account.color, "log", worker_name)
    if len(account.settings.links) > 0:
        link = random.choice(account.settings.links)
    else:
        status, id, name, screen_name, followers_count, pinned_tweet_id = await get_model_info(twttr_client, account, worker_name)

        if not status:
            add_message("Не удалось получить ссылку", account.screen_name, account.color, "error", worker_name)
            return False
        
        if pinned_tweet_id and len(pinned_tweet_id) > 0:
            link = f"https://x.com/{account.screen_name}/status/{pinned_tweet_id[0]}"

    return link


async def get_message_text(link:str, account:Account, inbox:bool=False, new:bool=False, no_tweet:bool=False, did_pinned:bool=False):
    text = f"{random.choice(account.settings.text_for_exist) if len(account.settings.text_for_exist) > 0 else 'Hello! RTxRT?'}\n\n"
    pinned = ""
    fake = ""

    if inbox:
        text = f"{random.choice(account.settings.text_for_inbox) if len(account.settings.text_for_inbox) > 0 else 'Okay! But you first!'}"
    elif new:
        text = f"{random.choice(account.settings.text_for_new) if len(account.settings.text_for_new) > 0 else 'Hello! RTxRT?'}"
    elif no_tweet:
        text = f"{random.choice(account.settings.text_for_no_tweet) if len(account.settings.text_for_no_tweet) > 0 else 'Sorry, i havent found tweet in your message/pinned. Send it again please!'}"
    elif did_pinned:
        text = f"{random.choice(account.settings.text_if_did_pinned) if len(account.settings.text_if_did_pinned) > 0 else 'I did your pinned!'}"
    
    if len(account.settings.text_for_pinned) > 0:
        pinned = f"\n\n{random.choice(account.settings.text_for_pinned)}\n"

    if len(account.settings.text_dont_fake) > 0:
        fake = f"{random.choice(account.settings.text_dont_fake)}\n\n"

    return f"{text}\n\n{link}\n{link}{pinned}{fake}{random.choice(MANAGER_MESSAGE)}"


async def check_tweet(account:Account, tweet:Tweet):
    if account.settings.skip_hidden_ads and tweet.tweet_card:
        return False
    
    for word in account.settings.banned_words_in_tweet:
        if word.lower() in tweet.text.lower():
            return False
        
    for lang in account.settings.skip_lang:
        if lang.lower() == tweet.lang:
            return False
    
    return True


async def add_tweet_to_line(account: Account, tweet:Tweet, worker_name:str=None) -> None:
    if await is_tweet_did(account, tweet.id):
        return

    if tweet.views < account.settings.min_tweet_views_to_work:
        return
    
    if tweet.bookmark_count < account.settings.min_bookmark_count_to_work:
        return
    
    if tweet.favorite_count < account.settings.min_favorite_count_to_work:
        return
    
    if tweet.reply_count < account.settings.min_reply_count_to_work:
        return
    
    if account.settings.min_retweet_count_to_work > tweet.retweet_count:
        return
    
    if len(account.tweets_for_work) < 20:
        account.tweets_for_work.append(tweet)
        add_message("Твит добавлен в очередь для работы!", account.screen_name, account.color, "success", worker_name)


async def get_pinned_tweet(twttr_client:TwttrAPIClient, account:Account, user:User):
    if user.pinned_tweet_id is not None:
        user.pinned_tweet = await tweet_info(twttr_client, account, user.pinned_tweet_id)


async def new_action(account:Account, message:str=None, user_id:int=None, unrt_id:int=None, rt_id:int=None, ban_id:int=None, nu=False):
    while True:
        if nu and len(account.nu_actions) < 15:
            account.nu_actions.append((message, user_id, unrt_id, rt_id, ban_id))
            break
        elif not nu and  len(account.dm_actions) < 15:
            account.dm_actions.append((message, user_id, unrt_id, rt_id, ban_id))
            break
        else:
            await wait_delay(10)


async def do_action(twttr_client:TwttrAPIClient, account:Account, action:tuple):
    if not action:
        return False

    await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay)
    msg, user_id, unrt_id, rt_id, ban_id = action

    if unrt_id:
        await wait_delay(min_sec=account.settings.min_small_actions_delay, max_sec=account.settings.max_small_actions_delay)
        await unretweet(twttr_client, account, unrt_id)

    if rt_id:
        await wait_delay(min_sec=account.settings.min_small_actions_delay, max_sec=account.settings.max_small_actions_delay)
        await retweet(twttr_client, account, rt_id)

    if msg and user_id:
        await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.min_actions_delay)
        await send_dm(twttr_client, account, msg, user_id=user_id)

    if ban_id:
        await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay)
        if not await is_user_in_blacklist(account, ban_id):
            await ban(twttr_client, account, ban_id)
            await block_user(account, ban_id) 

    return True


async def cooldown(account: Account, worker_name:str=None):
    if account.is_cooldown:
        add_message(f"Кулдаун {account.settings.cooldown_seconds}с.", account.screen_name, account.color, "warning", worker_name)
        await wait_delay(sec=account.settings.cooldown_seconds)
        account.is_cooldown = False

    if account.soft_detected:
        await add_message(f"Автоматику спалили! Ожидание {account.settings.if_detected_cooldown_seconds}с.", account.screen_name, account.color, "warning", worker_name)
        await wait_delay(account.settings.if_detected_cooldown_seconds)
        account.soft_detected = False


async def check_banned_status(account:Account):
    if account.is_banned:
        raise AccountBanned("Забанен")
import asyncio
import random

from api.twttr_api import TwttrAPIClient
from api.utools_api import uToolsAPIClient
from functions.api import get_ct0_by_auth_token, get_model_info, tweet_info
from functions.basic import add_message, add_debug
from functions.data import check_if_model, get_interlocutor_id, get_user_from_user_list, get_conversation_last_links, check_last_message_time
from functions.database import (create_database_and_table, has_enough_time_passed,
                                create_shared_database, is_user_in_fakers, add_faker, is_tweet_did)
from functions.validators import validate_auth_token
from logic.classes import Account, Tweet, User
from logic.constants import MANAGER_MESSAGE
from logic.exceptions import AccountBanned

from .api import ban, init_dm, retweet, send_dm, unretweet, tweet_info
from .basic import wait_delay
from .database import block_user, is_user_in_blacklist
from .api import get_reposted_timeline


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
        return None, [], [], []

    if  account.settings.skip_inbox:
        return maximal_entry, [], [], []

    return maximal_entry, messages, conversations, users

async def check_user(user:User, account:Account, dm=False, dbg:bool=False, inbox:bool=False):
    if dm and not inbox:
        checker = False
    elif dm and inbox:
        checker = True
    elif not dm:
        checker = True

    if user.id == account.id:
        add_debug("Это я", account.screen_name, account.color, dbg=dbg)
        return False

    if not user:
        add_debug("Нет пользователя", account.screen_name, account.color, dbg=dbg)
        return False
    
    if user.followers_count < account.settings.followers_to_work and checker:
        add_debug(f"Мало подписоты (@{user.screen_name}): {user.followers_count}/{account.settings.followers_to_work}", account.screen_name, account.color, dbg=dbg)
        return False
    
    if user.followers_count > account.settings.max_followers_to_work and checker and not inbox:
        add_debug("Слишком много подписоты", account.screen_name, account.color, dbg=dbg)
        return False
    
    if not user.is_blue_verified and not account.settings.work_with_not_blue_verified:
        add_debug("Галочки нет", account.screen_name, account.color, dbg=dbg)
        return False
    
    if not account.settings.work_if_not_sure_that_its_model and not await check_if_model(user.description, user.urls):
        add_debug("Не модель", account.screen_name, account.color, dbg=dbg)
        return False 
    
    if not user.can_dm:
        add_debug("Нельзя писать", account.screen_name, account.color, dbg=dbg)
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
    if len(account.settings.links) > 0:
        account.did_links += 1
        link = account.settings.links[account.did_links-1]
        if account.did_links == len(account.settings.links):
            account.did_links = 0
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
    if not tweet:
        return

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


async def new_action(account:Account, message:str=None, user_id:int=None, conversation_id:str=None, unrt_id:int=None, rt_id:int=None, ban_id:int=None, nu=False):
    while True:
        if nu and len(account.nu_actions) < 15:
            account.nu_actions.append((message, user_id, conversation_id, unrt_id, rt_id, ban_id))
            break
        elif not nu and  len(account.dm_actions) < 15:
            account.dm_actions.append((message, user_id, conversation_id, unrt_id, rt_id, ban_id))
            break
        else:
            await wait_delay(10)


async def do_action(twttr_client:TwttrAPIClient, account:Account, action):
    if not action:
        return False

    await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay)
    msg, user_id, conversation_id, unrt_id, rt_id, ban_id = action

    if unrt_id:
        await wait_delay(min_sec=account.settings.min_small_actions_delay, max_sec=account.settings.max_small_actions_delay)
        await unretweet(twttr_client, account, unrt_id)

    if rt_id:
        await wait_delay(min_sec=account.settings.min_small_actions_delay, max_sec=account.settings.max_small_actions_delay)
        await retweet(twttr_client, account, rt_id)

    if msg and user_id:
        await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.min_actions_delay)
        await send_dm(twttr_client, account, msg, user_id=user_id)

    if msg and conversation_id:
        await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.min_actions_delay)
        await send_dm(twttr_client, account, msg, conversation_id=conversation_id)

    if ban_id:
        await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay)
        if not await is_user_in_blacklist(account, ban_id):
            await ban(twttr_client, account, ban_id)
            await block_user(account, ban_id) 

    return True


async def cooldown(twttr_client: TwttrAPIClient, account: Account, worker_name:str=None):
    if account.is_cooldown:
        if not account.self_rts and account.settings.do_self_rts:
            add_message(f"Делаю селф-рт перед кулдауном", account.screen_name, account.color, "warning", worker_name)
            account.self_rts = True
            i = 0
            for id in account.settings.post_ids_for_cooldown_rt:
                if i == account.settings.max_self_rts_amount:
                    break
                await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay)
                tweet = await tweet_info(twttr_client, account, id)
                if tweet:
                    if tweet.retweeted:
                        await unretweet(twttr_client, account, id)
                        await wait_delay(min_sec=account.settings.min_small_actions_delay, max_sec=account.settings.max_small_actions_delay)
                    await retweet(twttr_client, account, id)
                i += 1
                add_message(f"{i}/{len(account.settings.post_ids_for_cooldown_rt) if len(account.settings.post_ids_for_cooldown_rt) < account.settings.max_self_rts_amount else account.settings.max_self_rts_amount} селф-рт сделано", account.screen_name, account.color, "warning", worker_name)

        add_message(f"Кулдаун {account.settings.cooldown_seconds}с.", account.screen_name, account.color, "warning", worker_name)

        await wait_delay(sec=account.settings.cooldown_seconds)
        account.is_cooldown = False
        account.self_rts = False

    if account.soft_detected:
        await add_message(f"Автоматику спалили! Ожидание {account.settings.if_detected_cooldown_seconds}с.", account.screen_name, account.color, "warning", worker_name)
        await wait_delay(account.settings.if_detected_cooldown_seconds)
        account.soft_detected = False

    if account.rate_limit:
        await wait_delay(43200)
        account.rate_limit = False


async def if_user_retweeted(twttr_client: TwttrAPIClient, account: Account, user_id: int, tweet_id: int, WORKER_NAME:str=None):
    cursor = ""

    amount = 0

    while True:
        cursor, users = await get_reposted_timeline(twttr_client, account, tweet_id, cursor, WORKER_NAME)
        amount += len(users)
        for user in users:
            if user.id == user_id:
                return True
            
        if not cursor:
            return False
        
        await wait_delay(sec=1)


async def procces_conversations(twttr_client:TwttrAPIClient, account: Account, conversations:list, messages:list, users:list, empty_pages:int, link:str=None, worker_name:str=None, inbox:bool=False):
    for conversation in conversations:
        await cooldown(twttr_client, account, worker_name)

        if len(account.settings.links) >= 1:
            link = await get_link_to_promote(twttr_client, account, worker_name)

        if not link:
            return -1

        if conversation.type == "GROUP_DM" and account.settings.skip_groups:
            continue
        elif conversation.type == "GROUP_DM" and not account.settings.skip_groups:
            if not await has_enough_time_passed(account, conversation.id, account.settings.minutes_before_next_interaction_with_group, worker_name):
                continue
            message = await get_message_text(link, account)
            await new_action(account=account, message=message, user_id=None, conversation_id=conversation.id, rt_id=None, unrt_id=None, ban_id=None)
            continue

        user_id = await get_interlocutor_id(conversation, account.id)
        user = await get_user_from_user_list(user_id, users)

        model_tweet_id, user_tweet_id = await get_conversation_last_links(conversation.id, account.id, messages)
        tweet = None

        if not await has_enough_time_passed(account, user_id, account.settings.minutes_before_next_interaction_with_exist, worker_name):
            print("Время 1")
            continue

      #  if not await check_last_message_time(conversation.id, messages, account.settings.minutes_before_next_interaction_with_exist):
       #     print("Время")
        #    continue

        if not await check_user_for_critical(user, account):
            if account.settings.ban_if_user_banned_you:
                await new_action(account=account, message=None, user_id=None, conversation_id=None, rt_id=None, unrt_id=None, ban_id=user_id)
            continue

        if not await check_user(user, account, dm=True, dbg=True, inbox=inbox):
            continue

        message = await get_message_text(link, account)

        if model_tweet_id and account.settings.check_retweets and not await if_user_retweeted(twttr_client, account, user_id, model_tweet_id, worker_name) and not inbox:
            if account.settings.send_msg_if_not_rt:
                await new_action(account=account, message=message, user_id=user_id)
                continue

            if await is_user_in_fakers(account, user_id, worker_name):
                await new_action(account=account, message=f"{random.choice(account.settings.faker_block_text)}", user_id=user_id, conversation_id=None, rt_id=None, unrt_id=None, ban_id=user_id)
                continue
                    
            await new_action(account=account, message=f"{random.choice(account.settings.warning_text)}", user_id=user_id, conversation_id=None, rt_id=None, unrt_id=None, ban_id=None)
            await add_faker(account, user_id, worker_name)
            continue

        if user_tweet_id:
            await wait_delay(min_sec=account.settings.min_small_actions_delay, max_sec=account.settings.max_small_actions_delay, worker_name=worker_name)
            tweet = await tweet_info(twttr_client, account, user_tweet_id, worker_name)
            
        empty_pages = 0

        if not tweet and not inbox:
            user.pinned_tweet = await get_pinned_tweet(twttr_client, account, user)
            tweet = user.pinned_tweet
            message = await get_message_text(link, account, did_pinned=True)

        if not tweet and not inbox:
            message = await get_message_text(link, account, no_tweet=True)
            await new_action(account=account, message=message, user_id=user_id, conversation_id=None, rt_id=None, unrt_id=None, ban_id=None)
            continue

        if account.settings.enable_nu_worker and tweet:
            await add_tweet_to_line(account, tweet, worker_name)

        if tweet and not await check_tweet(account, tweet):
            if account.settings.ban_if_bad_post:
                await new_action(account=account, message=None, user_id=None, conversation_id=None, rt_id=None,unrt_id=None, ban_id=user_id,)
                continue
            elif account.settings.send_msg_if_bad_post:
                await new_action(account=account, message=message, user_id=user_id)
                continue

        if not inbox:
            message = await get_message_text(link, account)
            await new_action(account=account, message=message, user_id=user_id, conversation_id=None, rt_id=tweet.id, unrt_id=tweet.id if tweet.retweeted else None, ban_id=None)
        else:
            message = await get_message_text(link, account, inbox=True)
            await new_action(account=account, message=message, user_id=user_id, conversation_id=None, rt_id=None, unrt_id=None, ban_id=None)
    
    print(empty_pages)
    return empty_pages
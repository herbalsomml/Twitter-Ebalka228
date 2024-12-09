import asyncio

from api.twttr_api import TwttrAPIClient
from api.utools_api import uToolsAPIClient
from functions.api import (get_dms,
                           get_reposted_timeline, init_dm, tweet_info)
from functions.basic import add_message, send_telegram_message, wait_delay, add_debug
from functions.data import (get_conversation_last_links, get_interlocutor_id,
                            get_user_from_user_list, check_last_message_time)
from functions.database import (add_tweet_to_db, has_enough_time_passed,
                                is_user_in_blacklist, is_user_in_db, add_faker, is_user_in_fakers)
from functions.workers import (add_tweet_to_line,
                               check_tweet, check_user,
                               check_user_for_critical, cooldown, do_action,
                               get_link_to_promote, get_message_text,
                               get_pinned_tweet, initialize, new_action, if_user_retweeted, initialize_dm, procces_conversations)
from logic.classes import Account
from logic.exceptions import AccountBanned
import random


async def dm_worker(twttr_client: TwttrAPIClient, utools_client: uToolsAPIClient, account: Account, WORKER_NAME:str):
    await cooldown(twttr_client, account, WORKER_NAME)
    id_for_pagination, messages, conversations, users = await initialize_dm(utools_client, twttr_client, account)
    if not id_for_pagination:
        add_message("Не удалось проинициализировать DM", account.screen_name, account.color, type="error")
        return False
    
    link = None
    if len(account.settings.links) < 1:
        link = await get_link_to_promote(twttr_client, account, WORKER_NAME)

    s = await procces_conversations(twttr_client, account, conversations, messages, users, 0, link, WORKER_NAME, inbox=True)

    if s == -1:
        return False
    
    empty_pages = 0
    while True:
        await cooldown(twttr_client, account, WORKER_NAME)
        id_for_pagination, messages, conversations, users = await get_dms(utools_client, twttr_client, account, id_for_pagination, WORKER_NAME)
        if not id_for_pagination:
            return False

        if len(conversations) < 1:
            empty_pages += 1

        if empty_pages >= account.settings.skip_after_empty_pages:
            return True
        
        if len(conversations) >= 1:
            link = None
            if len(account.settings.links) < 1:
                link = await get_link_to_promote(twttr_client, account, WORKER_NAME)

            s = await procces_conversations(twttr_client, account, conversations, messages, users, empty_pages, link, WORKER_NAME)
            empty_pages = 0

            if s == -1:
                return False

        await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay, worker_name=WORKER_NAME)


async def new_users_worker(twttr_client: TwttrAPIClient, account: Account, WORKER_NAME:str):
    await cooldown(twttr_client, account, WORKER_NAME)
    if len(account.settings.start_tweets) < 1 and len(account.tweets_for_work) < 1:
        return

    for tweet_id in account.settings.start_tweets:
        try:
            account.settings.start_tweets.remove(tweet_id)
            tweet_id = int(tweet_id)
            tweet = await tweet_info(twttr_client, account, tweet_id, WORKER_NAME)
            if tweet:
                account.tweets_for_work.append(tweet)
            else:
                add_message("Не удалось получить информацию о твите", account.screen_name, account.color, WORKER_NAME)
        except:
            add_message("В стартовых твитах должны быть указаны ID твитов", account.screen_name, account.color, WORKER_NAME)
                
        await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay, worker_name=WORKER_NAME)

    for tweet in account.tweets_for_work:
        await cooldown(twttr_client, account, WORKER_NAME)
        account.tweets_for_work.remove(tweet)
        cursor = ""

        if len(account.settings.links) < 1:
            link = await get_link_to_promote(twttr_client, account, WORKER_NAME)

        while True:
            cursor, users = await get_reposted_timeline(twttr_client, account, tweet.id, cursor, WORKER_NAME)
            for user in users:
                if not await check_user(user, account):
                    continue
                    
                if await is_user_in_blacklist(account, user.id, WORKER_NAME):
                    continue

                await wait_delay(min_sec=account.settings.min_small_actions_delay, max_sec=account.settings.max_small_actions_delay)

                await cooldown(twttr_client, account, WORKER_NAME)

                if await is_user_in_db(account, user.id, WORKER_NAME):
                #if await check_if_messages_in_conversation(twttr_client, account, user_id=user.id, worker_name=WORKER_NAME):
                    if not await has_enough_time_passed(account, user.id, account.settings.minutes_before_attempt_for_new_dm):
                        continue

                if len(account.settings.links) >= 1:
                    link = await get_link_to_promote(twttr_client, account, WORKER_NAME)
                if not link:
                    return False

                message = await get_message_text(link, account, new=True)
                await new_action(account=account, message=message, user_id=user.id, conversation_id=None, rt_id=None, unrt_id=None, ban_id=None, nu=True)
                await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay)

            if not cursor:
                await add_tweet_to_db(account, tweet.id)
                break

        await wait_delay(min_sec=account.settings.min_actions_delay, max_sec=account.settings.max_actions_delay, worker_name=WORKER_NAME)


async def action_maker_worker(twttr_client: TwttrAPIClient, account: Account, WORKER_NAME: str):
    await cooldown(twttr_client, account, WORKER_NAME)
    stop_worker = False

    while not stop_worker:
        action = None

        if not account.nu_actions and not account.dm_actions:
            stop_worker = True

        if account.actions_counter % account.settings.actions_steps == 0 and account.nu_actions:
            await asyncio.sleep(25)
            await cooldown(twttr_client, account, WORKER_NAME)
            action = account.nu_actions.pop(0)
        elif account.dm_actions:
            await cooldown(twttr_client, account, WORKER_NAME)
            action = account.dm_actions.pop(0)
            if account.settings.new_user_only_after_exist:
                account.actions_counter += 1

        if not account.settings.new_user_only_after_exist:
            account.actions_counter += 1

        await cooldown(twttr_client, account, WORKER_NAME)
        action_status =  await do_action(twttr_client, account, action)
        if action_status:
            account.done_actions_counter += 1

        add_message(f"Выполнено: {account.done_actions_counter}", account.screen_name, account.color, "log")


async def cooldown_controller(account:Account):
    while True:
        done_actions = account.done_actions_counter
        if done_actions > 0 and done_actions % account.settings.cooldown_every_steps == 0:
            account.is_cooldown = True
            while account.is_cooldown:
                await asyncio.sleep(5)
            account.done_actions_counter += 1

        await asyncio.sleep(15)


async def main_worker(account):
    twttr_client = TwttrAPIClient(account)
    utools_client = uToolsAPIClient(account)

    stop_worker = False

    try:
        init_status = await initialize(twttr_client, utools_client, account)
    except AccountBanned:
        await twttr_client.close()
        await utools_client.close()
        return
    if not init_status:
        add_message(f"❌ Не удалось пройти инициализацию", type="error")
        send_telegram_message(f"❌ Не удалось пройти инициализацию!", account.screen_name)
        return
        
    tasks = []

    async def run_worker(worker_name, worker_func):
        while True:
            try:
                task = asyncio.create_task(worker_func())
                tasks.append(task)
                await task
                await asyncio.sleep(15)
            except AccountBanned as e:
                stop_worker.set()
                add_message(
                    f"✋ Воркер {worker_name} Остановлен",
                    account.screen_name,
                    account.color,
                    "error",
                )
                send_telegram_message(
                    f"✋ Воркер {worker_name} Остановлен",
                    account.screen_name,
                )
            except Exception as e:
                add_message(
                    f"❌ {worker_name} завершился с ошибкой: {e}",
                    account.screen_name,
                    account.color,
                    "error",
                )
                send_telegram_message(
                    f"❌ {worker_name} завершился с ошибкой: {e}",
                account.screen_name,
                )

                add_debug(f"Перезапуск...", account.screen_name, account.color, worker_name)
                await asyncio.sleep(15)

    async def stop_all_tasks():
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run_actions_maker_worker():
        WORKER_NAME = "AM"
        await run_worker(WORKER_NAME, lambda: action_maker_worker(twttr_client, account, WORKER_NAME))

    async def run_dm_worker():
        WORKER_NAME = "DM"
        if account.settings.enable_dm_worker:
            await run_worker(WORKER_NAME, lambda: dm_worker(twttr_client, utools_client, account, WORKER_NAME))

    async def run_new_users_worker():
        WORKER_NAME = "NU"
        if account.settings.enable_nu_worker:
            await run_worker(WORKER_NAME, lambda: new_users_worker(twttr_client, account, WORKER_NAME))

    async def run_cooldown_controller():
        WORKER_NAME = "CLDN"
        await run_worker(WORKER_NAME, lambda: cooldown_controller(account))

    try:
        await asyncio.gather(
            run_dm_worker(),
            run_new_users_worker(),
            run_cooldown_controller(),
            run_actions_maker_worker(),
        )
    except AccountBanned:
        await twttr_client.close()
        await utools_client.close()
        await stop_all_tasks()
    finally:
        await twttr_client.close()
        await utools_client.close()
        

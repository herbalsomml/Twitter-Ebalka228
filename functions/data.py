import re
from pprint import pprint
from datetime import datetime, timedelta, timezone

from api.twttr_api import TwttrAPIClient
from logic.classes import Account, Conversation, Message, Tweet, User
from logic.constants import MODEL_MARKERS

from .database import has_enough_time_passed, is_user_in_blacklist


async def check_if_model(description, urls):
    lower_description = description.lower()
    if any(p.lower() in lower_description for p in MODEL_MARKERS):
        return True
    
    if any(p.lower() in url.lower() for url in urls for p in MODEL_MARKERS):
        return True
    
    return False


async def get_interlocutor_id(conversation, model_id):
    for p in conversation.participants:
        if p != model_id:
            return p


async def get_conversation_name(twttr_client:TwttrAPIClient, conversation, model_id, users):
    if len(conversation.participants) > 2:
        return "GROUP"
    for id in conversation.participants:
        if id == model_id:
            continue
        for user in users:
            if user.id == id:
                return f"@{user.screen_name}"
        r = await twttr_client.get_user_by_id(id)
        data = r.get("data")
        user_result = data.get("user_result") if data else None
        result = user_result.get("result") if user_result else None
        legacy = result.get("legacy") if result else None

        screen_name = legacy.get("screen_name") if legacy else "UNKNOWN"
        return f"@{screen_name}"
    

def get_pinned_tweets(pinned_tweet_ids):
        ids = []
        if pinned_tweet_ids:
            for id in pinned_tweet_ids:
                ids.append(int(id))

        return ids


async def get_maximal_entry_id(conversations):
    last_maximal_entry_id = None
    for conversation in conversations:
        max_entry_id = conversation.max_entry_id
        if last_maximal_entry_id is None:
            last_maximal_entry_id = max_entry_id
        elif max_entry_id > last_maximal_entry_id:
            last_maximal_entry_id = max_entry_id

    return last_maximal_entry_id


async def convert_conversations(conversations_obj):
    conversations = []
    for obj in conversations_obj:
        obj = conversations_obj[obj]
        id = obj.get("conversation_id")
        type = obj.get("type")
        min_entry_id = int(obj.get('min_entry_id')) if obj.get('min_entry_id') else None
        max_entry_id = int(obj.get('max_entry_id')) if obj.get('max_entry_id') else None
        last_read_event_id = int(obj.get('last_read_event_id')) if obj.get('last_read_event_id') else None
        read_only = obj.get('read_only')
        trusted = obj.get('trusted')
        participants = [int(p.get('user_id')) for p in obj.get('participants')]
        status = obj.get('status')

        variables = [id, type, min_entry_id, max_entry_id, last_read_event_id, trusted, participants, status]

        if not all(var is not None for var in variables):
            continue

        conversations.append(Conversation(id, type, min_entry_id, max_entry_id, last_read_event_id, read_only, trusted, participants, status))

    return conversations


async def get_message_urls(data):
    if not data:
        return []
    urls = []
    entities = data.get('entities')
    attachment = data.get('attachment')
    entities_urls = entities.get('urls') if entities else None
    if entities_urls:
        for url in entities_urls:
            urls.append(url.get('expanded_url'))

    if attachment:
        for obj in attachment:
            obj = attachment.get(obj)
            if obj.get('expanded_url'):
                urls.append(obj.get('expanded_url'))

    return urls


async def convert_messages(messages_obj):
    messages = []
    for obj in messages_obj:
        message = obj.get("message")
        if message:
            data = message.get('message_data')
            id = int(message.get('id')) if message.get('id') else None
            conversation_id = message.get('conversation_id')
            time = int(message.get('time')) if message.get('time') else None
            sender_id = int(data.get('sender_id')) if data.get('sender_id') else None
            recipient_id = int(data.get('recipient_id')) if data.get('recipient_id') else None
            text = data.get('text') if data.get('text') else ""
            urls = await get_message_urls(data)
            variables = [id, conversation_id, time, sender_id, text, urls]

            if not all(var is not None for var in variables):
                continue

            messages.append(Message(id, conversation_id, time, sender_id, recipient_id, text, urls))

    return messages
    

async def get_user_from_user_list(user_id, user_list):
    for usr in user_list:
        if usr.id != user_id:
            continue
        else:
            return usr


async def get_user_urls(user_obj):
    urls = []
    if not user_obj.get('entities'):
        return []
        
    entities = user_obj.get('entities')
    description = entities.get('description')
    description_urls = None
    if description is not None:
        description_urls = description.get('urls')
    if description_urls  is not None:
        for url in description_urls:
            urls.append(url.get('expanded_url'))

    entities_url = entities.get('url')

    entities_urls = None
    if entities_url is not None:
        entities_urls = entities_url.get('urls')
    if entities_urls is not None:
        for url in entities_urls:
            urls.append(url.get('expanded_url'))

    return urls


async def get_pinned_tweet_id(user_obj):
    if not user_obj.get('pinned_tweet_ids_str'):
        return None
        
    return int(user_obj.get('pinned_tweet_ids_str')[0])


async def convert_user(twttr_client:TwttrAPIClient, account:Account, user_obj):
    legacy = user_obj.get("legacy")
    if not legacy:
        return None
    id = int(user_obj.get("rest_id")) if user_obj.get("rest_id") else None
    name = legacy.get("name")
    screen_name = legacy.get("screen_name")
    followers_count = int(legacy.get("followers_count")) if legacy.get("followers_count") else None
    description = legacy.get('description') if legacy.get('description') else ""
    urls = await get_user_urls(user_obj)
    blocking = user_obj.get('blocking') if user_obj.get('blocking') else False
    dm_blocking = user_obj.get('dm_blocking') if user_obj.get('dm_blocking') else False
    dm_blocked_by = user_obj.get('dm_blocked_by') if user_obj.get('dm_blocked_by') else False
    is_blue_verified = user_obj.get('is_blue_verified')
    created_at = legacy.get('created_at')
    can_dm = legacy.get('can_dm')
    pinned_tweet_id = await get_pinned_tweet_id(legacy)

    variables = [id, name, screen_name, followers_count, description,  urls, blocking, dm_blocking, dm_blocked_by, created_at]

    if not all(var is not None for var in variables):
        return None
    
    return User(id, name, screen_name, followers_count, description, urls, blocking, dm_blocking, dm_blocked_by, is_blue_verified, created_at, can_dm, pinned_tweet_id)
    

async def convert_users(twttr_client:TwttrAPIClient, account:Account, users_obj):
    users = []
    for obj in users_obj:
        obj = users_obj[obj]

        id = int(obj.get('id_str')) if obj.get('id_str') else None
        name = obj.get('name')
        screen_name = obj.get('screen_name')
        followers_count = int(obj.get('followers_count')) if obj.get('followers_count') else None
        description = obj.get('description') if obj.get('description') else ""
        urls = await get_user_urls(obj)
        blocking = obj.get('blocking')
        dm_blocking = obj.get('dm_blocking')
        dm_blocked_by = obj.get('dm_blocked_by')
        is_blue_verified = obj.get('is_blue_verified')
        created_at = obj.get('created_at')
        can_dm = obj.get('can_dm') if obj.get('can_dm') is not None else True
        pinned_tweet_id = await get_pinned_tweet_id(obj)

        variables = [id, name, screen_name, followers_count, description,  urls, blocking, dm_blocking, dm_blocked_by, created_at]

        if not all(var is not None for var in variables):
            continue

        users.append(User(id, name, screen_name, followers_count, description, urls, blocking, dm_blocking, dm_blocked_by, is_blue_verified, created_at, can_dm, pinned_tweet_id))

    return users


async def get_model_info_from_response(r):
    if len(r) <= 1:
        return False, None, None, None, None, None
        
    id = int(r.get('id_str')) if r.get('id_str') else None
    name = r.get("name")
    screen_name = r.get("screen_name")
    followers_count = int(r.get("followers_count")) if r.get("followers_count") else None
    pinned_tweet_id = get_pinned_tweets(r.get("pinned_tweet_ids_str")) if r.get("pinned_tweet_ids_str") else None

    return True, id, name, screen_name, followers_count, pinned_tweet_id

    
async def get_dm_init_data_from_response(twttr_client:TwttrAPIClient, account:Account, r):
    if len(r) < 3:
        return False, None, None, None
    
    data = r.get('data')
    inbox_initial_state = data.get('inbox_initial_state') if data else None
    conversations_obj = inbox_initial_state.get('conversations')
    messages_obj = inbox_initial_state.get('entries')
    users_obj = inbox_initial_state.get('users')

    conversations = await convert_conversations(conversations_obj) if conversations_obj else []
    messages = await convert_messages(messages_obj) if messages_obj else []
    users = await convert_users(twttr_client, account, users_obj) if users_obj else []

    return True, messages, conversations, users


async def get_dm_list_data_from_response(twttr_client:TwttrAPIClient, account:Account, r, worker_name:str=None):
    if len(r) < 3:
        return False, None, None, None, None
    
    data = r.get("data")
    inbox_timeline = data.get("inbox_timeline") if data else None
    min_entry_id = inbox_timeline.get('min_entry_id') if inbox_timeline else None

    if not data or not inbox_timeline or not min_entry_id:
        return False, None, [], [], []
    
    conversations_obj = inbox_timeline.get("conversations")
    conversations = await convert_conversations(conversations_obj)
    messages_obj = inbox_timeline.get('entries')
    messages = await convert_messages(messages_obj) 
    users_obj = inbox_timeline.get('users')
    users = await convert_users(twttr_client, account, users_obj)

    ## Отладочная
    status = inbox_timeline.get("status")
    if status != "HAS_MORE":
        pprint(data)
        print(status)
        exit()

    sorted_messages = await get_sorted_messages(messages)
    sorted_conversations = await get_sorted_conversations(account, messages, conversations, worker_name)

    return True, min_entry_id, sorted_messages, sorted_conversations, users


async def get_tweet_data_from_response(r):
    data = r.get("data")
    tweet_result = data.get("tweet_result") if data else None

    if tweet_result is None:
        return
    
    result = tweet_result.get("result")

    if result is None:
        return
    
    typename = result.get("__typename")

    if typename == "TweetUnavailable":
        return
    elif typename == "Tweet":
        id = int(result.get("rest_id"))
        legacy = result.get("legacy")
        view_count_info = result.get("view_count_info")
        tweet_card = result.get("tweet_card")
    elif typename == "TweetWithVisibilityResults":
        tweet = result.get("tweet")
        if tweet is None:
            return
        
        id = int(tweet.get("rest_id"))
        legacy = tweet.get("legacy")
        view_count_info = tweet.get("view_count_info")
        tweet_card = tweet.get("tweet_card")
    
    views = int(view_count_info.get("count")) if view_count_info else 0
    
    if legacy is None:
        return
    
    bookmark_count = int(legacy.get("bookmark_count")) if legacy.get("bookmark_count") else 0
    bookmarked = legacy.get("bookmarked")
    favorite_count = int(legacy.get("favorite_count")) if legacy.get("favorite_count") else 0
    favorited = legacy.get("favorited")
    text = legacy.get("full_text") if legacy.get("full_text") else ""
    is_quote_status = legacy.get("is_quote_status")
    reply_count = int(legacy.get("reply_count")) if legacy.get("reply_count") else 0
    retweet_count = int(legacy.get("retweet_count")) if legacy.get("retweet_count") else 0
    retweeted = legacy.get("retweeted")
    lang = legacy.get("lang")

    return Tweet(id, views, tweet_card, bookmark_count, bookmarked, favorite_count, favorited, text, is_quote_status, reply_count, retweet_count, retweeted, lang)


async def extract_id_from_url(url):
    match = re.search(r"status/(\d+)", url)
    if match:
        return int(match.group(1))
    return None


async def get_conversation_last_links(conversation_id, model_id, messages):
    model_post_id = None
    user_post_id = None
    link = None

    for message in messages:
        if message.conversation_id != conversation_id:
            continue
        
        if len(message.urls) < 1:
            continue

        for url in message.urls:
            if '/status/' in url:
                link = url
                break
        
        if message.sender_id == model_id and model_post_id is None:
            model_post_id = await extract_id_from_url(link) if link else None
        elif user_post_id is None:
            user_post_id = await extract_id_from_url(link) if link else None

        if model_post_id and user_post_id:
            break
    
    return model_post_id, user_post_id


async def get_sorted_messages(messages):
    sorted_messages = sorted(
        [msg for msg in messages],
        key=lambda x: x.time,
        reverse=True
    )

    return sorted_messages


async def check_last_message_time(conversation_id, messages, minutes_before_next_interaction_with_exist):
    conversation_messages = [msg for msg in messages if msg.conversation_id == conversation_id]
    
    if not conversation_messages:
        return True
    
    last_message = max(conversation_messages, key=lambda msg: msg.time)
    
    last_message_timestamp = datetime.fromtimestamp(last_message.time / 1000, tz=timezone.utc)
    
    now = datetime.now(tz=timezone.utc)
    
    time_since_last_message = now - last_message_timestamp
    minutes_passed = time_since_last_message.total_seconds() / 60
    
    return minutes_passed > minutes_before_next_interaction_with_exist


async def check_conversation(account:Account, conversation, messages, worker_name:str=None):
    if conversation.read_only:
        return False

    if not await check_last_message_time(conversation.id, messages, account.settings.minutes_before_next_interaction_with_exist):
        return False
    
    if not conversation.trusted:
        return False
    
    user_id = await get_interlocutor_id(conversation, account.id)
    
    for id in account.settings.ignor_user_ids:
        if id == user_id:
            return False

    if await is_user_in_blacklist(account, user_id, worker_name):
        return False

    if account.settings.skip_readed and conversation.max_entry_id <= conversation.last_read_event_id:
        return False
    
    return True


async def get_sorted_conversations(account:Account, messages, conversations, worker_name:str=None):
    sorted_conversations = []
    for msg in messages:
        for conversation in conversations:
            if not await check_conversation(account, conversation, messages, worker_name):
                continue
            if msg.conversation_id == conversation.id and conversation not in sorted_conversations:
                sorted_conversations.append(conversation)
    
    return sorted_conversations

async def get_inbox_conversations(conversations: list):
    sorted = []
    for conversation in conversations:
        if not conversation.trusted:
            sorted.append(conversation)

    return sorted


async def get_reposted_timeline_data_from_response(twttr_client:TwttrAPIClient, account:Account, r, worker_name:str=None):
    if len(r) < 1:
        return None, []
    
    cursor = None
    users = []
    
    data = r.get("data")
    timeline_response = data.get("timeline_response") if data else None
    timeline = timeline_response.get('timeline') if timeline_response else None
    instructions = timeline.get("instructions") if timeline else None

    if not data or not timeline_response or not timeline or not instructions:
        return None, []
    
    for inst in instructions:
        entries = inst.get("entries")
        if not entries:
            continue

        if len(entries) <= 2:
            continue

        for entry in entries:
            content = entry.get("content")
            if not content:
                continue

            typename = content.get("__typename")

            if typename == "TimelineTimelineCursor":
                cursorType = content.get("cursorType")
                if cursorType == "Bottom":
                    cursor = content.get("value")
                continue

            content_2 = content.get("content")
            if not content_2:
                continue

            typename_2 = content_2.get("__typename")

            if typename_2 != "TimelineUser":
                continue
            
            userResult = content_2.get("userResult")

            if "result" not in userResult:
                continue

            result = userResult.get("result")

            user = await convert_user(twttr_client, account, result)
            if user is not None:
                users.append(user)
   
    return cursor, users


async def get_model_info_from_response(r):
    if len(r) <= 1:
        return False, None, None, None, None, None
        
    id = int(r.get('id_str')) if r.get('id_str') else None
    name = r.get("name")
    screen_name = r.get("screen_name")
    followers_count = int(r.get("followers_count")) if r.get("followers_count") else None
    pinned_tweet_id = get_pinned_tweets(r.get("pinned_tweet_ids_str")) if r.get("pinned_tweet_ids_str") else None

    return True, id, name, screen_name, followers_count, pinned_tweet_id


async def check_if_messages_in_conversation_from_response(r):
    conversation_timeline = r.get("conversation_timeline")
    if not conversation_timeline:
        return False

    status = conversation_timeline.get("status")
    entries = conversation_timeline.get("entries")
    if not entries:
        return False
    
    return True
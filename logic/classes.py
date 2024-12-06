from .constants import TEXT_INBOX, TEXT_PINNED, TEXT_DONT_FAKE, TEXT_FOR_NEW, TEXT_FOR_NOT_FOUND, TEXT_IF_DID_PINNED, BANNED_WORDS, TEXT_FOR_EXIST, WARNING_TEXT, FAKER_BLOCK_TEXT

class Settings:
    def __init__(self,
                 start_tweets:list=[],
                 links:list=[],
                 post_ids_for_cooldown_rt:list=[],

                 ban_id_bad_post:bool=True,
                 ban_if_user_banned_you:bool=True,
                 skip_after_empty_pages:int=15,
                 actions_steps:int=2,
                 cooldown_every_steps:int=100,
                 followers_to_work:int=15000,
                 work_with_not_blue_verified:bool=True,
                 work_if_not_sure_that_its_model:bool=True,
                 min_bookmark_count_to_work:int=0,
                 min_favorite_count_to_work:int=0,
                 min_reply_count_to_work:int=0,
                 min_retweet_count_to_work:int=0,
                 min_tweet_views_to_work:int=0,
                 new_user_only_after_exist:bool=False,
                 do_self_rts:bool=False,
                 max_followers_to_work:int=400000,

                 banned_words_in_tweet:list=BANNED_WORDS,
                 skip_lang:list=[],
                 ignor_user_ids:list=[],
                 max_self_rts_amount:int=15,

                 skip_hidden_ads:bool=True,
                 check_retweets:bool=True,
                 skip_readed:bool=True,
                 skip_groups:bool=True,
                 skip_inbox:bool=True,

                 text_for_inbox:list=TEXT_INBOX,
                 text_for_pinned:list=TEXT_PINNED,
                 text_dont_fake:list=TEXT_DONT_FAKE,
                 text_for_new:list=TEXT_FOR_NEW,
                 text_for_exist:list=TEXT_FOR_EXIST,
                 text_for_no_tweet:list=TEXT_FOR_NOT_FOUND,
                 text_if_did_pinned:list=TEXT_IF_DID_PINNED,
                 warning_text:list=WARNING_TEXT,
                 faker_block_text:list=FAKER_BLOCK_TEXT,

                 minutes_before_next_interaction_with_exist:int=60,
                 minutes_before_attempt_for_new_dm:int=10080,
                 min_actions_delay:int=10,
                 max_actions_delay:int=20,
                 min_small_actions_delay:int=5,
                 max_small_actions_delay:int=10,
                 cooldown_seconds:int=2400,
                 if_detected_cooldown_seconds:int=900,

                 enable_dm_worker:bool=True,
                 enable_nu_worker:bool=True
    ):
        ## Стартовые настройки
        self.start_tweets = start_tweets
        self.links = links
        self.post_ids_for_cooldown_rt = post_ids_for_cooldown_rt

        ## Настройки
        self.ban_id_bad_post = ban_id_bad_post
        self.ban_if_user_banned_you = ban_if_user_banned_you
        self.skip_after_empty_pages = skip_after_empty_pages
        self.actions_steps = actions_steps
        self.cooldown_every_steps = cooldown_every_steps
        self.new_user_only_after_exist = new_user_only_after_exist
        self.do_self_rts = do_self_rts
        
        ## Ограничители
        self.followers_to_work = followers_to_work
        self.work_with_not_blue_verified = work_with_not_blue_verified
        self.work_if_not_sure_that_its_model = work_if_not_sure_that_its_model
        self.min_bookmark_count_to_work = min_bookmark_count_to_work
        self.min_favorite_count_to_work = min_favorite_count_to_work
        self.banned_words_in_tweet = banned_words_in_tweet
        self.min_reply_count_to_work = min_reply_count_to_work
        self.min_retweet_count_to_work = min_retweet_count_to_work
        self.min_tweet_views_to_work = min_tweet_views_to_work
        self.skip_lang = skip_lang
        self.ignor_user_ids = ignor_user_ids
        self.max_self_rts_amount = max_self_rts_amount
        self.max_followers_to_work = max_followers_to_work
        

        ### Функции
        self.skip_hidden_ads = skip_hidden_ads
        self.check_retweets = check_retweets
        self.skip_readed = skip_readed
        self.skip_groups = skip_groups
        self.skip_inbox = skip_inbox


        ### Тексты
        self.text_for_inbox = text_for_inbox
        self.text_for_pinned = text_for_pinned
        self.text_dont_fake = text_dont_fake
        self.text_for_new = text_for_new
        self.text_for_exist = text_for_exist
        self.text_for_no_tweet = text_for_no_tweet
        self.text_if_did_pinned = text_if_did_pinned
        self.warning_text = warning_text
        self.faker_block_text = faker_block_text
        
        ## Задержки
        self.minutes_before_next_interaction_with_exist = minutes_before_next_interaction_with_exist
        self.minutes_before_attempt_for_new_dm = minutes_before_attempt_for_new_dm

        self.min_actions_delay = min_actions_delay
        self.max_actions_delay = max_actions_delay
        self.min_small_actions_delay = min_small_actions_delay
        self.max_small_actions_delay = max_small_actions_delay
        self.cooldown_seconds = cooldown_seconds
        self.if_detected_cooldown_seconds = if_detected_cooldown_seconds

        self.enable_dm_worker = enable_dm_worker
        self.enable_nu_worker = enable_nu_worker

class Account:
    def __init__(
            self, proxy: str,
            screen_name: str,
            session: str,
            auth_token: str,
            color: str,
            settings: Settings
    ):
        self.proxy = proxy if isinstance(proxy, str) else None
        self.screen_name = screen_name
        self.session = session if isinstance(session, str) else None
        self.auth_token = auth_token if isinstance(auth_token, str) else None
        self.ct0 = None
        self.color = color if color and isinstance(color, str) else "#dfe6e9"
        self.settings = settings if isinstance(settings, Settings) else None

        self.name = None
        self.id = None
        self.followers_count = None
        self.pinned_tweets = None

        self.tweets_for_work = []
        self.dm_actions = []
        self.nu_actions = []
        self.actions_counter = 0
        self.done_actions_counter = 0
        self.is_cooldown = False
        self.soft_detected = False

        self.self_rts = False


class User:
    def __init__(self, id, name, screen_name, followers_count, description, urls, blocking, dm_blocking, dm_blocked_by, is_blue_verified, created_at, can_dm, pinned_tweet_id):
        self.id = id
        self.name = name
        self.screen_name = screen_name
        self.followers_count = followers_count
        self.description = description
        self.urls = urls
        self.blocking = blocking
        self.dm_blocking = dm_blocking
        self.dm_blocked_by = dm_blocked_by
        self.is_blue_verified = is_blue_verified
        self.created_at = created_at
        self.can_dm = can_dm
        self.pinned_tweet_id = pinned_tweet_id
        self.pinned_tweet = None


class Message:
    def __init__(self, id:int, conversation_id:str, time:int, sender_id:int, recipient_id:int, text:str, urls:list):
        self.id = id
        self.conversation_id = conversation_id
        self.time = time
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.text = text
        self.urls = urls


class Conversation:
    def __init__(self, id:int, type:str, min_entry_id:int, max_entry_id:int, last_read_event_id:int, read_only:bool, trusted:bool, participants:list, status:str):
        self.id = id
        self.type = type
        self.min_entry_id = min_entry_id
        self.max_entry_id = max_entry_id
        self.last_read_event_id = last_read_event_id
        self.read_only = read_only
        self.trusted = trusted
        self.participants = participants
        self.status = status


class Tweet:
    def __init__(self, id:int, views:int, tweet_card, bookmark_count:int, bookmarked:bool, favorite_count:int, favorited:bool, text:str, is_quote_status:bool, reply_count:int, retweet_count:int, retweeted:bool, lang:str):
        self.id = id
        self.views = views
        self.tweet_card = tweet_card
        self.bookmark_count = bookmark_count
        self.bookmarked = bookmarked
        self.favorite_count = favorite_count
        self.favorited = favorited
        self.text = text
        self.is_quote_status = is_quote_status
        self.reply_count = reply_count
        self.retweet_count = retweet_count
        self.retweeted = retweeted
        self.lang = lang

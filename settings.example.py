from logic.classes import Account, Settings

############
### База ###
############
twttr_api_key = "api_key twttr api"
utools_api_key = "api_key utools api"
reconnect_retries = 15
retry_backoff = 2

telegram_ids = [
    1435333610
]
telegram_bot_api_key = "8135380565:AAFIYfHS1B1ytbyRreCJrgLnnU04P90HHNU"

##############
### Текста ###
##############
text_for_inbox = [
    "Okay, but you go first! 🤔",
    "...",
    "..."
]
text_for_pinned = [
    "📌 If the link won't open, retweet my pinned post! 🔁",
    "...",
    "..."
]
text_dont_fake = [
    "⛔ Fake = Ban! Don't try it! 🚫",
    "..."
]
text_for_new = [
    "Hello! 👋 Retweet for Retweet? 🔄",
    "..."
]
text_for_exist = [
    "Done! ✔️ RT for RT again? 🔄",
    "..."
]
text_for_no_tweet = [
    "Sorry, I didn't find the tweet in your message/pinned. Please send it again! 🔄",
    "..."
]
text_if_did_pinned = [
    "Link is not working! I did your pinned! 📌",
    "..."
]


#################
### Настройки ###
#################
settings = Settings(
    start_tweets=[
        12341234,
        12341234
    ],
    links=[
        "https://pornhub.com/"
    ],
    
    ban_id_bad_post=True,
    ban_if_user_banned_you=True,
    skip_after_empty_pages=50,
    actions_steps=5,
    cooldown_every_steps=100,
    followers_to_work=15000,
    work_with_not_blue_verified=True,
    work_if_not_sure_that_its_model=True,
    min_bookmark_count_to_work=0,
    min_favorite_count_to_work=0,
    min_reply_count_to_work=0,
    min_retweet_count_to_work=0,
    min_tweet_views_to_work=0,

    banned_words_in_tweet=[
        "putin"
    ],
    skip_lang=[
        "zh"
    ],
    ignor_user_ids=[
        123412234,
        12341234
    ],
    
    skip_hidden_ads=True,
    check_retweets=True,
    skip_readed=True,
    skip_groups=True,
    skip_inbox=True,

    text_for_inbox=text_for_inbox,
    text_for_pinned=text_for_pinned,
    text_dont_fake=text_dont_fake,
    text_for_new=text_for_new,
    text_for_exist=text_for_exist,
    text_for_no_tweet=text_for_no_tweet,
    text_if_did_pinned=text_if_did_pinned,

    minutes_before_next_interaction_with_exist=60,
    minutes_before_attempt_for_new_dm=10080,
    min_actions_delay=10,
    max_actions_delay=20,
    min_small_actions_delay=5,
    max_small_actions_delay=10,
    cooldown_seconds=900,
    if_detected_cooldown_seconds=900
)



################
### Аккаунты ###
################
account = Account(
    "Прокси без протокола",
    "screen_name",
    "сессия twttr_api",
    "auth_token",
    "#00cec9",
    settings
)
accounts_list = [
    account
]

import asyncio

import aiohttp

from functions.basic import add_message, send_telegram_message
from logic.classes import Account
from logic.exceptions import Error
from settings import reconnect_retries, retry_backoff, twttr_api_key
from logic.exceptions import AccountBanned


class TwttrAPIClient:
    def __init__(self, account: Account):
        self.api_key = twttr_api_key
        self.base_url = "https://twttrapi.p.rapidapi.com/"
        self.twttr_session = account.session
        self.twttr_proxy = f"http://{account.proxy}"
        self.session = aiohttp.ClientSession()
        self.max_retries = reconnect_retries
        self.retry_backoff = retry_backoff

        self.account = account


    def _get_headers(self):
        return {
            "twttr-session": self.twttr_session,
            "twttr-proxy": self.twttr_proxy,
            "x-rapidapi-host": "twttrapi.p.rapidapi.com",
            "x-rapidapi-key": self.api_key,
            "content-type": "application/json",
        }


    async def _send_request(self, method, endpoint, params=None, json=None):
        url = self.base_url + endpoint
        headers = self._get_headers()

        if method == "POST":
            headers["content-type"] = "application/x-www-form-urlencoded"

        retries = 0
        while retries < self.max_retries:
            if method == "GET":
                async with self.session.get(
                    url, headers=headers, params=params
                ) as response:
                    try:
                        response.raise_for_status()
                        d = await response.json()
                        success_indicator = d.get('success')

                        if success_indicator is not None and success_indicator == False:
                            raise Error(d.get("error"))
                        return d
                    except aiohttp.ClientResponseError as e:
                        if "Too Many Requests" in str(e):
                            add_message(f"Too Many Requests. Слишком много запросов или закончился тариф.", self.account.name, self.account.color, "error")
                            await asyncio.sleep(self.retry_backoff ** retries)
                            retries += 1
                        else:
                            raise Error(f"HTTP Error: {e}")
                    except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
                        add_message(f"Connection error: {e}. Retrying in {self.retry_backoff ** retries} seconds...", self.account.name, self.account.color, "warning")
                        await asyncio.sleep(self.retry_backoff ** retries)
                        retries += 1
            elif method == "POST":
                async with self.session.post(
                    url, headers=headers, data=json
                ) as response:
                    try:
                        response.raise_for_status()
                        d = await response.json()
                        success_indicator = d.get('success')

                        if success_indicator is not None and success_indicator == False:
                            raise Error(d.get("error"))
                        return d
                    except aiohttp.ClientResponseError as e:
                        if "Too Many Requests" in str(e):
                            add_message(f"Too Many Requests. Слишком много запросов или закончился тариф.", self.account.name, self.account.color, "error")
                            await asyncio.sleep(self.retry_backoff ** retries)
                            retries += 1
                        else:
                            raise Error(f"HTTP Error: {e}")
                    except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
                        add_message(f"Connection error: {e}. Retrying in {self.retry_backoff ** retries} seconds...", self.account.name, self.account.color, "warning")
                        await asyncio.sleep(self.retry_backoff ** retries)
                        retries += 1
        raise Error(f"Max retries exceeded for endpoint {endpoint}")


    async def close(self):
        await self.session.close()


    async def get_user_by_id(self, id=None):
        endpoint = "get-user-by-id"
        params = {
            "user_id": id
        }
        return await self._send_request("GET", endpoint, params=params)

    async def get_user(self, username):
        endpoint = "get-user"
        params = {
            "username": username
        }
        return await self._send_request("GET", endpoint, params=params)
    
    async def send_dm(self, message, to_user_id="", to_user_name="", media_id=""):
        endpoint = "send-dm"
        payload = {
            "message": message,
            "to_user_id": to_user_id,
            "to_user_name": to_user_name,
            "media_id": media_id
        }
        return await self._send_request("POST", endpoint, json=payload)
    

    async def retweet_tweet(self, tweet_id):
        endpoint = "retweet-tweet"
        payload = {
            "tweet_id": tweet_id
        }
        return await self._send_request("POST", endpoint, json=payload)
    

    async def unretweet_tweet(self, tweet_id):
        endpoint = "unretweet-tweet"
        payload = {
            "tweet_id": tweet_id
        }
        return await self._send_request("POST", endpoint, json=payload)

    async def get_tweet_info(self, tweet_id):
        endpoint = "get-tweet"
        params = {
            "tweet_id": tweet_id
        }
        return await self._send_request("GET", endpoint, params=params)
    
    async def block_user(self, user_id):
        endpoint = "block-user"
        payload = {
            "user_id": user_id
        }
        return await self._send_request("POST", endpoint, json=payload)
    
    async def reposted_timeline(self, tweet_id, cursor=""):
        endpoint = "reposted-timeline"
        params = {
            "cursor": cursor,
            "tweet_id": tweet_id
        }
        return await self._send_request("GET", endpoint, params)
    
    async def get_dm_conversation(self, user_id:int=None):
        endpoint = "get-dm-conversation"
        params = {
            "user_id": user_id,
        }
        return await self._send_request("GET", endpoint, params)
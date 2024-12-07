import asyncio

import aiohttp

from functions.basic import add_message, add_debug
from logic.classes import Account
from logic.exceptions import Error
from settings import utools_api_key


class uToolsAPIClient:
    def __init__(self, account:Account):
        self.api_key = utools_api_key
        self.base_url = "https://twitter.good6.top/api/base/apitools/"
        self.auth_token = account.auth_token
        self.ct0 = account.ct0 if account.ct0 else "ct0"
        self.proxy = f"https://{account.proxy}"
        self.session = aiohttp.ClientSession()
        self.resFormat = "json"
        self.max_retries = 15
        self.retry_backoff = 2
        self.account = account

    def _get_headers(self):
        return {"accept": "*/*"}

    async def _send_request(self, method, endpoint, params=None, data=None):
        url = self.base_url + endpoint
        headers = self._get_headers()

        if method == "POST":
            headers["content-type"] = "application/x-www-form-urlencoded"

        params.update(
            {
                "apiKey": self.api_key,
                "auth_token": self.auth_token,
                "ct0": self.ct0,
                "proxyUrl": self.proxy,
                "resFormat": self.resFormat,
            }
        )

        retries = 0
        while retries < self.max_retries:
            try:
                while True:
                    async with self.session.request(
                        method, url, headers=headers, params=params, data=data, timeout=10
                    ) as response:
                        response.raise_for_status()
                        d = await response.json()
                        code = d.get("code")
                        msg = d.get("msg")

                        if code == 0:
                            if "If your parameters contain auth_token, please check whether the account status is normal." in msg:
                                add_debug("Глюк utools, новая попытка")
                                asyncio.sleep(5)
                                continue
                            raise Error(msg)
                        return d

            except aiohttp.ClientResponseError as e:
                raise Error(f"HTTP Error: {e}")

            except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
                add_message(f"Connection error: {e}. Retrying in {self.retry_backoff ** retries} seconds...", self.account.screen_name, self.account.color, "warning")
                await asyncio.sleep(self.retry_backoff ** retries)
                retries += 1

        raise Error(f"Max retries exceeded for endpoint {endpoint}")

    async def close(self):
        await self.session.close()

    async def get_user_id_by_auth_token(self):
        endpoint = "getUserIdByToken"
        params = {}
        return await self._send_request("GET", endpoint, params=params)

    async def get_ct0_by_auth_token(self):
        endpoint = "getCt0"
        params = {}
        return await self._send_request("GET", endpoint, params=params)

    async def get_dms_init(self, cursor=''):
        endpoint = "getDMSInitIdV2"
        params = {"cursor": cursor}
        return await self._send_request("GET", endpoint, params=params)


    async def get_dms_list(self, max_id):
        endpoint = "getDMSListV2"
        params = {"max_id": max_id}
        return await self._send_request("GET", endpoint, params=params)
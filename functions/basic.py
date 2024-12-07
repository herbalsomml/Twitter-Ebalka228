import asyncio
import random

import requests
from colorama import Fore, Style
from rich.console import Console
from settings import debug

from settings import telegram_bot_api_key, telegram_ids


def send_telegram_message(message, account_name:str=None):
    if not telegram_bot_api_key or len(telegram_ids) < 0:
        return
    
    url = f"https://api.telegram.org/bot{telegram_bot_api_key}/sendMessage"

    for id in telegram_ids:
        if account_name:
            name_str = f" | <code>{account_name}</code>"
        else:
            name_str = ""
        payload = {
            "chat_id": id,
            "text": f"<b>{message}</b>{name_str}",
            "parse_mode": "HTML"
        }
        try:

            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
        except Exception as e:
            add_message(f"Ошибка при отправке сообщения в телеграм: {e}", type="error")


async def wait_delay(sec:int = 10, min_sec:int = None, max_sec:int = None, worker_name:str=None):
    if min_sec is not None and max_sec is not None:
        sec = random.randint(min_sec, max_sec)
    
    await asyncio.sleep(sec)


def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip('#')
    
    r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
    
    return f"\033[38;2;{r};{g};{b}m"


def add_message(msg:str, info:str="...", color:str="#FFFFFF", type:str="success", worker:str=None):
    info_colored = hex_to_rgb(color)
    
    if type == "error":
        msg_color = Fore.RED
    elif type == "success":
        msg_color = Fore.GREEN
    elif type == "log":
        msg_color = Fore.CYAN
    elif type == "warning":
        msg_color = Fore.YELLOW
    else:
        msg_color = Fore.WHITE

    print(Fore.LIGHTBLACK_EX + "------------" + Style.RESET_ALL)
    print(Fore.LIGHTBLACK_EX + f"{info_colored}{info} | {Fore.WHITE + worker + ' | ' if worker else ''}" + msg_color + msg + Style.RESET_ALL)


def add_debug(msg:str, info:str="...", color:str="#FFFFFF", worker:str=None, dbg:bool=False):
    if debug and dbg:
        info_colored = hex_to_rgb(color)
        print(Fore.LIGHTBLACK_EX + "------------" + Style.RESET_ALL)
        print(Fore.LIGHTBLACK_EX + f"{info_colored}{info} | {Fore.WHITE + worker + ' | ' if worker else ''}" + Fore.WHITE + msg + Style.RESET_ALL)


async def stop_tasks(tasks: list):
    for task in tasks:
        task.cancel()

    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

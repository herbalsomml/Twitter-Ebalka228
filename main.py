import asyncio

from art import *
from colorama import Fore, Style

from functions.basic import add_message, send_telegram_message
from functions.validators import validate_account
from logic.workers import main_worker
from settings import accounts_list


async def main():
    art = text2art("Twitter EBAKA228")
    print(Fore.RED + art + Style.RESET_ALL)

    tasks = []
    for account in accounts_list:
        if await validate_account(account):
            tasks.append(asyncio.create_task(main_worker(account)))

    if tasks:
        await asyncio.gather(*tasks)
        add_message(msg="✅ Все задачи завершены. Программа завершена.", type="warning")
        send_telegram_message("✅ Все задачи завершены. Программа завершена.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(Fore.RED + f"Ошибка выполнения: {e}" + Style.RESET_ALL)
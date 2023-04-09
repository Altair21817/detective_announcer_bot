# -*- coding: UTF-8 -*-

import asyncio
import json
import logging
# from telegram.ext import CommandHandler
# from telegram.ext import 
from telegram.ext import Filters, MessageHandler, Updater, CallbackQueryHandler, CallbackContext

from project.data.app_data import (
    APP_JSON_FOLDER, API_TELEGRAM_UPDATE_SEC, API_VK_UPDATE_SEC, TEAM_CONFIG,
    TEAM_NAME, TELEGRAM_BOT_TOKEN, TELEGRAM_TEAM_CHAT, TELEGRAM_USER,
    VK_TOKEN_ADMIN, VK_USER, VK_GROUP_TARGET)
import project.app_logger as app_logger
from project.app_telegram import (
    check_telegram_bot_response, init_telegram_bot,
    rebuild_team_config_game_dates, send_message, send_update)
from project.app_vk import (
    define_post_topic, get_vk_wall_update, init_vk_bot, parse_post)

ALL_DATA: tuple[str] = (
    TEAM_NAME,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_TEAM_CHAT,
    TELEGRAM_USER,
    VK_TOKEN_ADMIN,
    VK_USER,
    VK_GROUP_TARGET)

logger: logging.Logger = app_logger.get_logger(__name__)


def check_env(data: list) -> None:
    """Checks env data."""
    if not all(data):
        logger.critical('Env data is empty!')
        raise SystemExit
    return


def json_data_read(file_name: str, key: str = None) -> any:
    """Read json file and return it's data.
    If there is no file or no given key if data - return 0.
    Optional: return certain value for given key."""
    try:
        with open(f'{APP_JSON_FOLDER}{file_name}') as read_file:
            data: dict[str] = json.load(read_file)
        if key:
            return data[key]
        return data
    except FileNotFoundError:
        logger.info(f"JSON '{file_name}' doesn't exists.")
    except KeyError:
        logger.info(f"JSON doesn't contain key '{key}'.")
    return 0


def json_data_write(file_name: str, write_data: dict) -> None:
    """Write given data to json file. Create new if not exists."""
    with open(f'{APP_JSON_FOLDER}{file_name}', 'w') as write_file:
        json.dump(write_data, write_file)
    return


async def vk_listener(
        last_vk_wall_id: int,
        team_config: dict,
        telegram_bot,
        vk_bot) -> None:
    """Use VK API for checking updates from target VK group.
    If new post available - parse it and sent to target telegram chat."""
    while 1:
        logger.debug('Try to receive data from VK group wall.')
        # update: dict = get_vk_wall_update(
        #     last_vk_wall_id=last_vk_wall_id['last_vk_wall_id'],
        #     vk_bot=vk_bot,
        #     vk_group_id=VK_GROUP_TARGET)
        from tests import vk_wall_examples
        update = vk_wall_examples.EXAMPLE_PREVIEW
        # EXAMPLE_CHECKIN
        # EXAMPLE_PRIZE_RESULTS
        # EXAMPLE_TEAMS
        # EXAMPLE_GAME_RESULTS
        # EXAMPLE_RATING
        # EXAMPLE_OTHER
        # EXAMPLE_PREVIEW
        if update:
            logger.info('New post available!')
            topic: str = define_post_topic(post=update)
            parsed_post: dict = parse_post(post=update, post_topic=topic)
            if parsed_post:
                send_update(
                    parsed_post=parsed_post,
                    team_config=team_config,
                    telegram_bot=telegram_bot)
                json_data_write(
                    file_name='last_vk_wall_id.json',
                    write_data={'last_vk_wall_id': parsed_post['post_id']})
                last_vk_wall_id['last_vk_wall_id'] = parsed_post['post_id']
        logger.debug(f'vk_listener sleep for {API_VK_UPDATE_SEC} sec.')
        await asyncio.sleep(API_VK_UPDATE_SEC)


async def telegram_listener(team_config: dict) -> None:
        
        def handle_callback_query(update, context):
            query = update.callback_query
            username: str = query.from_user.username
            game_num, decision = query.data.split()
            rebuild_team_config_game_dates(
                team_config=team_config,
                teammate_decision={
                    'teammate': username,
                    'game_num': int(game_num),
                    'decision': int(decision)})
            
        
        updater: Updater = Updater(token=TELEGRAM_BOT_TOKEN)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))
        updater.start_polling(poll_interval=API_TELEGRAM_UPDATE_SEC)



async def spam_in_console(team_config) -> None:
    """For test asyncio work. Spam text in console."""
    while 1:
        print('SpamSpamSpamSpamSpamSpamSpam')
        await asyncio.sleep(2)


async def main():
    """Main program. Manage vk_listener and telegram_listener."""
    logger.info('Program is running.')
    check_env(data=ALL_DATA)
    check_telegram_bot_response(token=TELEGRAM_BOT_TOKEN)
    vk_bot = init_vk_bot(
        token=VK_TOKEN_ADMIN, user_id=VK_USER)
    telegram_bot = init_telegram_bot(token=TELEGRAM_BOT_TOKEN)
    # last_api_error: str = json_data_read(file_name='last_api_error.json')
    last_vk_wall_id: dict = json_data_read(file_name='last_vk_wall_id.json')
    if not last_vk_wall_id:
        last_vk_wall_id = {'last_vk_wall_id': 0}
    team_config: dict = json_data_read(file_name='team_config.json')
    if not team_config:
        team_config = TEAM_CONFIG
    logger.info('Data check succeed. All API are available. Start polling.')
    task_telegram = asyncio.create_task(
        telegram_listener(team_config=team_config))
    task_vk = asyncio.create_task(
        vk_listener(
            last_vk_wall_id=last_vk_wall_id,
            team_config=team_config,
            telegram_bot=telegram_bot,
            vk_bot=vk_bot))
    task_spam = asyncio.create_task(spam_in_console(team_config))
    await asyncio.gather(task_spam, task_telegram, task_vk)
    # while 1:
    #     try:
    #         await asyncio.gather(task_vk, task_spam)
    #         # telegram_listener()
    #     except SystemExit as err:
    #         """\033[31mError in code.
    #         Program execution is not possible.\033[0m"""
    #         logger.critical(err)
    #         raise
    #     except Exception as err:
    #         """\033[33mError on the API side.
    #         The program will continue to run normally.[0m"""
    #         # last_api_error: str = json_data_read(file_name=last_api_error)
    #         # if err != last_api_error:
    #         #     pass
    #         logger.warning(err)
    #         pass

if __name__ == '__main__':
    asyncio.run(main())

import asyncio
import datetime
import logging
import json
import os.path
import sys
import socket
import time
from tkinter import messagebox

from aiofile import AIOFile
from async_timeout import timeout
from aionursery import MultiError
import configargparse

import gui_chat_client as gui
from gui_common import TkAppClosed
from utils import create_handy_nursery, get_sanitized_text


watchdog_logger = logging.getLogger('watchdog')


class InvalidToken(Exception):
    pass


async def load_json_data(filepath):
    if not os.path.exists(filepath):
        return None

    async with AIOFile(filepath) as file_object:
        return json.loads(await file_object.read())


def add_datetime_info(text):
    now = datetime.datetime.now()
    return f'[{now.strftime("%d.%m.%Y %H:%M")}] {text}'


async def write_to_file(file_object, text, enable_adding_datetime_info=True):
    text = add_datetime_info(text) if enable_adding_datetime_info else text

    await file_object.write(text)
    await file_object.fsync()


async def save_messages(output_filepath, messages_queue):
    async with AIOFile(output_filepath, 'a') as file_object:
        while True:
            message = await messages_queue.get()
            await write_to_file(file_object=file_object, text=message)


async def watch_for_connection(
        watchdog_messages_queue, max_pending_time_between_messages=4):
    while True:
        try:
            async with timeout(max_pending_time_between_messages) as timeout_manager:
                message = await watchdog_messages_queue.get()
        except asyncio.TimeoutError:
            if not timeout_manager.expired:
                raise
            watchdog_logger.warning(
                f'[{int(time.time())}] '
                f'{max_pending_time_between_messages}s timeout is elapsed',
            )
            raise ConnectionError

        watchdog_logger.debug(
            f'[{int(time.time())}] Connection is alive. {message}',
        )


async def run_chat_reader(
        host, port, displayed_messages_queue, written_to_file_messages_queue,
        status_updates_queue, watchdog_messages_queue, successful_connection_info_queue):
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)

    reader, writer = await asyncio.open_connection(host=host, port=port)

    try:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
        successful_connection_info_queue.put_nowait(True)

        while True:
            message = await reader.readline()

            displayed_messages_queue.put_nowait(f'{message.decode().strip()}')
            written_to_file_messages_queue.put_nowait(f'{message.decode()}')
            watchdog_messages_queue.put_nowait('New message in chat')
    finally:
        writer.close()
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)


async def authorise(reader, writer, auth_token, watchdog_messages_queue):
    greeting_message = await reader.readline()
    watchdog_messages_queue.put_nowait('Prompt before auth')

    writer.write(f'{auth_token}\n'.encode())
    await writer.drain()

    user_credentials_message = await reader.readline()
    watchdog_messages_queue.put_nowait('Authorisation done')

    user_credentials = json.loads(user_credentials_message.decode())

    if user_credentials is None:
        return None

    welcome_to_chat_message = await reader.readline()
    watchdog_messages_queue.put_nowait('Welcome to chat message received')

    return user_credentials


async def send_message(reader, writer, message, watchdog_messages_queue):
    sending_message = f'{get_sanitized_text(message)}\n\n' if message else '\n'

    writer.write(sending_message.encode())
    await writer.drain()

    successfully_sent_message = await reader.readline()
    watchdog_messages_queue.put_nowait('Message sent')


async def send_empty_messages(
        reader, writer, watchdog_messages_queue,
        timeout_between_sending_messages=2):
    while True:
        await send_message(
            reader=reader,
            writer=writer,
            message='',
            watchdog_messages_queue=watchdog_messages_queue,
        )
        await asyncio.sleep(timeout_between_sending_messages)


async def send_messages(
        reader, writer, sending_messages_queue, watchdog_messages_queue):
    while True:
        message = await sending_messages_queue.get()

        if message:
            await send_message(
                reader=reader,
                writer=writer,
                message=message,
                watchdog_messages_queue=watchdog_messages_queue,
            )


async def run_chat_writer(
        host, port, auth_token, sending_messages_queue, status_updates_queue,
        watchdog_messages_queue, successful_connection_info_queue):
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)

    reader, writer = await asyncio.open_connection(host=host, port=port)

    try:
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
        successful_connection_info_queue.put_nowait(True)

        user_credentials = await authorise(
            reader=reader,
            writer=writer,
            auth_token=auth_token,
            watchdog_messages_queue=watchdog_messages_queue,
        )
        if user_credentials is None:
            raise InvalidToken()

        status_updates_queue.put_nowait(
            gui.NicknameReceived(user_credentials["nickname"]),
        )

        async with create_handy_nursery() as nursery:
            nursery.start_soon(
                send_messages(
                    reader=reader,
                    writer=writer,
                    sending_messages_queue=sending_messages_queue,
                    watchdog_messages_queue=watchdog_messages_queue,
                ),
            )
            nursery.start_soon(
                send_empty_messages(
                    reader=reader,
                    writer=writer,
                    watchdog_messages_queue=watchdog_messages_queue,
                ),
            )
    finally:
        writer.close()
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)


def get_command_line_arguments():
    parser = configargparse.ArgumentParser()

    parser.add_argument(
        '--host',
        help='Host for connect to chat. Required',
        env_var='CHAT_HOST',
        type=str,
        required=True,
    )
    parser.add_argument(
        '--read-port',
        help='Port for connect to chat for reading messages. Default: 5000',
        env_var='CHAT_READ_PORT',
        type=int,
        default=5000,
    )
    parser.add_argument(
        '--write-port',
        help='Port for connect to chat for writing messages. Default: 5050',
        env_var='CHAT_WRITE_PORT',
        type=int,
        default=5050,
    )
    parser.add_argument(
        '--credentials',
        help='Path to the file with user credentials. Default: user_credentials.json',
        env_var='USER_CREDENTIALS_FILEPATH',
        type=str,
        default='user_credentials.json',
    )
    parser.add_argument(
        '--token',
        help='User token for authorisation in chat. '
             'If given, then auth token from file with user credentials will be ignored',
        env_var='CHAT_AUTH_TOKEN',
        type=str,
        default='',
    )
    parser.add_argument(
        '--output',
        help='Filepath for save chat messages. Default: chat.txt',
        env_var='CHAT_MESSAGES_OUTPUT_FILEPATH',
        type=str,
        default='chat.txt',
    )
    return parser.parse_args()


async def handle_connection(
        host, read_port, write_port, auth_token, displayed_messages_queue,
        written_to_file_messages_queue, sending_messages_queue,
        status_updates_queue, connection_attempts_count_without_timeout=2,
        timeout_between_connection_attempts=2):
    watchdog_messages_queue = asyncio.Queue()
    chat_reader_successful_connection_info_queue = asyncio.Queue()
    chat_writer_successful_connection_info_queue = asyncio.Queue()

    current_connection_attempt = 0

    while True:
        try:
            current_connection_attempt += 1

            async with create_handy_nursery() as nursery:
                nursery.start_soon(
                    run_chat_reader(
                        host=host,
                        port=read_port,
                        displayed_messages_queue=displayed_messages_queue,
                        written_to_file_messages_queue=written_to_file_messages_queue,
                        status_updates_queue=status_updates_queue,
                        watchdog_messages_queue=watchdog_messages_queue,
                        successful_connection_info_queue=chat_reader_successful_connection_info_queue,
                    ),
                )
                nursery.start_soon(
                    run_chat_writer(
                        host=host,
                        port=write_port,
                        auth_token=auth_token,
                        sending_messages_queue=sending_messages_queue,
                        status_updates_queue=status_updates_queue,
                        watchdog_messages_queue=watchdog_messages_queue,
                        successful_connection_info_queue=chat_writer_successful_connection_info_queue,
                    ),
                )
                nursery.start_soon(
                    watch_for_connection(
                        watchdog_messages_queue=watchdog_messages_queue,
                    ),
                )
            return
        except MultiError as e:
            for exc in e.exceptions:
                if not isinstance(exc, socket.gaierror):
                    raise
        except (ConnectionError, socket.gaierror):
            pass

        if (not chat_reader_successful_connection_info_queue.empty() and
                not chat_writer_successful_connection_info_queue.empty()):
            current_connection_attempt = 0

        if not chat_reader_successful_connection_info_queue.empty():
            chat_reader_successful_connection_info_queue.get_nowait()

        if not chat_writer_successful_connection_info_queue.empty():
            chat_writer_successful_connection_info_queue.get_nowait()

        if current_connection_attempt >= connection_attempts_count_without_timeout:
            await asyncio.sleep(timeout_between_connection_attempts)


async def main():
    command_line_arguments = get_command_line_arguments()

    chat_host = command_line_arguments.host
    chat_read_port = command_line_arguments.read_port
    chat_write_port = command_line_arguments.write_port
    user_credentials_filepath = command_line_arguments.credentials
    chat_auth_token = command_line_arguments.token
    output_filepath = command_line_arguments.output

    if not chat_auth_token:
        user_credentials = await load_json_data(user_credentials_filepath)

        if not user_credentials:
            sys.exit('Auth token not given')

        chat_auth_token = user_credentials['account_hash']

    displayed_messages_queue = asyncio.Queue()
    written_to_file_messages_queue = asyncio.Queue()
    sending_messages_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    watchdog_logger.setLevel(level=logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level=logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(name)s:%(levelname)s:%(message)s'))
    watchdog_logger.addHandler(console_handler)

    async with create_handy_nursery() as nursery:
        nursery.start_soon(
            handle_connection(
                host=chat_host,
                read_port=chat_read_port,
                write_port=chat_write_port,
                auth_token=chat_auth_token,
                displayed_messages_queue=displayed_messages_queue,
                written_to_file_messages_queue=written_to_file_messages_queue,
                sending_messages_queue=sending_messages_queue,
                status_updates_queue=status_updates_queue,
            ),
        )
        nursery.start_soon(
            gui.draw(
                messages_queue=displayed_messages_queue,
                sending_queue=sending_messages_queue,
                status_updates_queue=status_updates_queue,
            ),
        )
        nursery.start_soon(
            save_messages(
                output_filepath=output_filepath,
                messages_queue=written_to_file_messages_queue,
            ),
        )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except InvalidToken:
        messagebox.showerror('Invalid token', 'Unknown token. Check it')
        sys.exit(1)
    except (KeyboardInterrupt, TkAppClosed):
        pass

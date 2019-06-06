import asyncio
import datetime
import logging
import json
import sys
import time
from contextlib import asynccontextmanager
from tkinter import messagebox

from aiofile import AIOFile
from async_timeout import timeout
import configargparse

import gui


class InvalidToken(Exception):
    pass


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


async def watch_for_connection(watchdog_messages_queue, max_timeout_between_messages=1):
    watchdog_logger = logging.getLogger('watchdog')
    watchdog_logger.setLevel(level=logging.DEBUG)

    while True:
        try:
            async with timeout(max_timeout_between_messages) as timeout_manager:
                message = await watchdog_messages_queue.get()
        except asyncio.TimeoutError:
            if not timeout_manager.expired:
                raise
            watchdog_logger.warning(
                f'[{int(time.time())}] {max_timeout_between_messages}s timeout is elapsed',
            )
            continue

        watchdog_logger.debug(
            f'[{int(time.time())}] Connection is alive. {message}',
        )


async def run_chat_reader(
        host, port, displayed_messages_queue, written_to_file_messages_queue,
        status_updates_queue, watchdog_messages_queue):
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)

    reader, writer = await asyncio.open_connection(host=host, port=port)

    try:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)

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
    logging.debug(f'Received: {greeting_message.decode().strip()}')
    watchdog_messages_queue.put_nowait('Prompt before auth')

    writer.write(f'{auth_token}\n'.encode())
    logging.debug(f'Sent: {auth_token}')

    user_credentials_message = await reader.readline()
    logging.debug(f'Received: {user_credentials_message.decode().strip()}')
    watchdog_messages_queue.put_nowait('Authorisation done')

    return json.loads(user_credentials_message.decode())


async def submit_message(reader, writer, message, watchdog_messages_queue):
    info_message = await reader.readline()
    logging.debug(f'Received: {info_message.decode().strip()}')
    watchdog_messages_queue.put_nowait('Prompt before message send')

    writer.write(f'{get_sanitized_text(message)}\n\n'.encode())
    logging.debug(f'Sent: {message}')


def get_sanitized_text(text):
    return text.replace('\n', '')


async def run_chat_writer(
        host, port, auth_token, sending_messages_queue, status_updates_queue,
        watchdog_messages_queue):
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)

    reader, writer = await asyncio.open_connection(host=host, port=port)

    try:
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)

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
        while True:
            message = await sending_messages_queue.get()
            await submit_message(
                reader=reader,
                writer=writer,
                message=message,
                watchdog_messages_queue=watchdog_messages_queue,
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
        '--token',
        help='User token for authorisation in chat.',
        env_var='CHAT_AUTH_TOKEN',
        type=str,
        default='',
    )
    parser.add_argument(
        '--nickname',
        help='User nickname for registering in chat.',
        env_var='CHAT_NICKNAME',
        type=str,
        default='',
    )
    parser.add_argument(
        '--output',
        help='Filepath for save chat messages. Default: chat.txt',
        env_var='OUTPUT_FILEPATH',
        type=str,
        default='chat.txt',
    )
    return parser.parse_args()


async def handle_connection(
        host, read_port, write_port, auth_token, displayed_messages_queue,
        written_to_file_messages_queue, sending_messages_queue,
        status_updates_queue):
    watchdog_messages_queue = asyncio.Queue()

    await asyncio.gather(
        run_chat_reader(
            host=host,
            port=read_port,
            displayed_messages_queue=displayed_messages_queue,
            written_to_file_messages_queue=written_to_file_messages_queue,
            status_updates_queue=status_updates_queue,
            watchdog_messages_queue=watchdog_messages_queue,
        ),
        run_chat_writer(
            host=host,
            port=write_port,
            auth_token=auth_token,
            sending_messages_queue=sending_messages_queue,
            status_updates_queue=status_updates_queue,
            watchdog_messages_queue=watchdog_messages_queue,
        ),
        watch_for_connection(
            watchdog_messages_queue=watchdog_messages_queue,
        ),
    )


async def main():
    command_line_arguments = get_command_line_arguments()

    chat_host = command_line_arguments.host
    chat_read_port = command_line_arguments.read_port
    chat_write_port = command_line_arguments.write_port
    chat_auth_token = command_line_arguments.token
    output_filepath = command_line_arguments.output

    logging.basicConfig(level=logging.DEBUG)

    if not chat_auth_token:
        sys.exit('Auth token not given')

    displayed_messages_queue = asyncio.Queue()
    written_to_file_messages_queue = asyncio.Queue()
    sending_messages_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(
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
        gui.draw(
            messages_queue=displayed_messages_queue,
            sending_queue=sending_messages_queue,
            status_updates_queue=status_updates_queue,
        ),
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
    except (KeyboardInterrupt, gui.TkAppClosed):
        pass

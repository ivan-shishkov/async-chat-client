import asyncio
import socket
import logging
import json
from tkinter import messagebox

import configargparse
from aiofile import AIOFile, Writer

import gui_chat_registrator as gui
from utils import create_handy_nursery


def get_sanitized_text(text):
    return text.replace('\n', '')


async def register(reader, writer, nickname):
    greeting_message = await reader.readline()
    logging.debug(f'Received: {greeting_message.decode().strip()}')

    writer.write('\n'.encode())
    logging.debug('Sent: empty line')

    enter_nickname_message = await reader.readline()
    logging.debug(f'Received: {enter_nickname_message.decode().strip()}')

    writer.write(f'{get_sanitized_text(nickname)}\n'.encode())
    logging.debug(f'Sent: {nickname}')

    user_credentials_message = await reader.readline()
    logging.debug(f'Received: {user_credentials_message.decode().strip()}')

    return json.loads(user_credentials_message.decode())


async def save_user_credentials(user_credentials, output_filepath):
    async with AIOFile(output_filepath, 'w') as file_object:
        writer = Writer(file_object)

        await writer(f'Your chat nickname: {user_credentials["nickname"]}\n')
        await writer(f'Your auth token: {user_credentials["account_hash"]}\n')


async def run_chat_registrator(
        host, port, sending_messages_queue,
        user_credentials_output_filepath='user_credentials.txt'):
    writer = None

    while True:
        try:
            nickname = await sending_messages_queue.get()

            reader, writer = await asyncio.open_connection(host=host, port=port)

            user_credentials = await register(
                reader=reader,
                writer=writer,
                nickname=nickname,
            )
            await save_user_credentials(
                user_credentials=user_credentials,
                output_filepath=user_credentials_output_filepath,
            )
            messagebox.showinfo(
                title='Successfully registered',
                message=f'Your credentials saved to {user_credentials_output_filepath}',
            )
            raise gui.TkAppClosed()

        except socket.gaierror:
            messagebox.showerror(
                title='Connection error',
                message='Could not connect to server. Check your internet connection',
            )
        finally:
            if writer:
                writer.close()


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
        '--port',
        help='Port for connect to chat. Default: 5050',
        env_var='CHAT_WRITE_PORT',
        type=int,
        default=5050,
    )
    return parser.parse_args()


async def main():
    command_line_arguments = get_command_line_arguments()

    chat_host = command_line_arguments.host
    chat_port = command_line_arguments.port

    sending_messages_queue = asyncio.Queue()

    logging.basicConfig(level=logging.DEBUG)

    async with create_handy_nursery() as nursery:
        nursery.start_soon(
            gui.draw(
                sending_queue=sending_messages_queue,
            ),
        )
        nursery.start_soon(
            run_chat_registrator(
                host=chat_host,
                port=chat_port,
                sending_messages_queue=sending_messages_queue,
            )
        )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, gui.TkAppClosed):
        pass

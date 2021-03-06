import asyncio
import socket
import json
from tkinter import messagebox

import configargparse
from aiofile import AIOFile
from async_timeout import timeout

import gui_chat_registrator as gui
from gui_common import TkAppClosed
from utils import create_handy_nursery, get_sanitized_text


class UserSuccessfullyRegistered(Exception):
    pass


class UserRegistrationPendingTimeElapsed(Exception):
    pass


async def register(reader, writer, nickname):
    greeting_message = await reader.readline()

    writer.write('\n'.encode())
    await writer.drain()

    enter_nickname_message = await reader.readline()

    writer.write(f'{get_sanitized_text(nickname)}\n'.encode())
    await writer.drain()

    user_credentials_message = await reader.readline()

    return json.loads(user_credentials_message.decode())


async def save_user_credentials(user_credentials, output_filepath):
    async with AIOFile(output_filepath, 'w') as file_object:
        await file_object.write(json.dumps(user_credentials))


async def execute_user_registration(
        reader, writer, nickname, max_pending_time_of_user_registration=2):
    try:
        async with timeout(max_pending_time_of_user_registration) as timeout_manager:
            user_credentials = await register(
                reader=reader,
                writer=writer,
                nickname=nickname,
            )
        return user_credentials

    except asyncio.TimeoutError:
        if not timeout_manager.expired:
            raise
        raise UserRegistrationPendingTimeElapsed()


async def run_chat_registrator(
        host, port, nickname_queue, register_button_state_queue,
        user_credentials_output_filepath):
    writer = None

    while True:
        try:
            nickname = await nickname_queue.get()

            reader, writer = await asyncio.open_connection(host=host, port=port)

            user_credentials = await execute_user_registration(
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
                message=f'Registered nickname: {user_credentials["nickname"]}\n'
                        f'Your credentials saved to {user_credentials_output_filepath}',
            )
            raise UserSuccessfullyRegistered()

        except socket.gaierror:
            messagebox.showerror(
                title='Connection error',
                message='Could not connect to server. Check your internet connection',
            )
        except UserRegistrationPendingTimeElapsed:
            messagebox.showerror(
                title='Registration pending time elapsed',
                message='User registration pending time elapsed. Try to register again',
            )
        finally:
            if writer:
                writer.close()
            register_button_state_queue.put_nowait('normal')


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
    parser.add_argument(
        '--output',
        help='Filepath for save user credentials. Default: user_credentials.json',
        env_var='USER_CREDENTIALS_FILEPATH',
        type=str,
        default='user_credentials.json',
    )
    return parser.parse_args()


async def main():
    command_line_arguments = get_command_line_arguments()

    chat_host = command_line_arguments.host
    chat_port = command_line_arguments.port
    user_credentials_output_filepath = command_line_arguments.output

    nickname_queue = asyncio.Queue()
    register_button_state_queue = asyncio.Queue()

    async with create_handy_nursery() as nursery:
        nursery.start_soon(
            gui.draw(
                nickname_queue=nickname_queue,
                register_button_state_queue=register_button_state_queue,
            ),
        )
        nursery.start_soon(
            run_chat_registrator(
                host=chat_host,
                port=chat_port,
                nickname_queue=nickname_queue,
                register_button_state_queue=register_button_state_queue,
                user_credentials_output_filepath=user_credentials_output_filepath,
            )
        )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, TkAppClosed, UserSuccessfullyRegistered):
        pass

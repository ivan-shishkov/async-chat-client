import asyncio
import socket
from contextlib import asynccontextmanager

import configargparse

import gui


@asynccontextmanager
async def open_connection(host, port):
    reader, writer = await asyncio.open_connection(host=host, port=port)
    try:
        yield reader, writer
    finally:
        writer.close()


async def read_messages(
        host, port, queue,
        connection_attempts_count_without_timeout=2,
        timeout_between_connection_attempts=3):
    current_connection_attempt = 0

    while True:
        try:
            current_connection_attempt += 1

            async with open_connection(host=host, port=port) as (reader, writer):
                current_connection_attempt = 0

                queue.put_nowait('Connection established')

                while True:
                    message = await reader.readline()
                    queue.put_nowait(f'{message.decode().strip()}')

        except (socket.gaierror, ConnectionRefusedError, ConnectionResetError):
            if current_connection_attempt < connection_attempts_count_without_timeout:
                queue.put_nowait('No connection. Retrying.')
            else:
                queue.put_nowait(
                    f'No connection. '
                    f'Retrying in {timeout_between_connection_attempts} sec.',
                )
                await asyncio.sleep(timeout_between_connection_attempts)


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


async def main():
    command_line_arguments = get_command_line_arguments()

    chat_host = command_line_arguments.host
    chat_read_port = command_line_arguments.read_port

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(
        gui.draw(
            messages_queue=messages_queue,
            sending_queue=sending_queue,
            status_updates_queue=status_updates_queue,
        ),
        read_messages(
            host=chat_host,
            port=chat_read_port,
            queue=messages_queue,
        ),
    )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

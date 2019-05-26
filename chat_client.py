import asyncio
import socket
import datetime
import logging
from contextlib import asynccontextmanager

from aiofile import AIOFile
import configargparse

import gui


def add_datetime_info(text):
    now = datetime.datetime.now()
    return f'[{now.strftime("%d.%m.%Y %H:%M")}] {text}'


async def write_to_file(file_object, text, enable_adding_datetime_info=True):
    text = add_datetime_info(text) if enable_adding_datetime_info else text

    await file_object.write(text)
    await file_object.fsync()


async def save_messages(output_filepath, queue):
    async with AIOFile(output_filepath, 'a') as file_object:
        while True:
            message = await queue.get()
            await write_to_file(file_object=file_object, text=message)


@asynccontextmanager
async def open_connection(host, port):
    reader, writer = await asyncio.open_connection(host=host, port=port)
    try:
        yield reader, writer
    finally:
        writer.close()


async def read_messages(
        host, port, displayed_messages_queue, written_to_file_messages_queue,
        connection_attempts_count_without_timeout=2,
        timeout_between_connection_attempts=3):
    current_connection_attempt = 0

    while True:
        try:
            current_connection_attempt += 1

            async with open_connection(host=host, port=port) as (reader, writer):
                current_connection_attempt = 0

                displayed_messages_queue.put_nowait('Connection established')
                written_to_file_messages_queue.put_nowait('Connection established\n')

                while True:
                    message = await reader.readline()
                    displayed_messages_queue.put_nowait(f'{message.decode().strip()}')
                    written_to_file_messages_queue.put_nowait(f'{message.decode()}')

        except (socket.gaierror, ConnectionRefusedError, ConnectionResetError):
            if current_connection_attempt < connection_attempts_count_without_timeout:
                displayed_messages_queue.put_nowait('No connection. Retrying.')
                written_to_file_messages_queue.put_nowait('No connection. Retrying.\n')
            else:
                displayed_messages_queue.put_nowait(
                    f'No connection. '
                    f'Retrying in {timeout_between_connection_attempts} sec.',
                )
                written_to_file_messages_queue.put_nowait(
                    f'No connection. '
                    f'Retrying in {timeout_between_connection_attempts} sec.\n',
                )
                await asyncio.sleep(timeout_between_connection_attempts)


async def send_messages(host, port, queue):
    while True:
        message = await queue.get()
        logging.debug(f'User wrote: {message}')


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
    chat_write_port = command_line_arguments.write_port
    output_filepath = command_line_arguments.output

    logging.basicConfig(level=logging.DEBUG)

    displayed_messages_queue = asyncio.Queue()
    written_to_file_messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(
        gui.draw(
            messages_queue=displayed_messages_queue,
            sending_queue=sending_queue,
            status_updates_queue=status_updates_queue,
        ),
        read_messages(
            host=chat_host,
            port=chat_read_port,
            displayed_messages_queue=displayed_messages_queue,
            written_to_file_messages_queue=written_to_file_messages_queue,
        ),
        save_messages(
            output_filepath=output_filepath,
            queue=written_to_file_messages_queue,
        ),
        send_messages(
            host=chat_host,
            port=chat_write_port,
            queue=sending_queue,
        ),
    )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

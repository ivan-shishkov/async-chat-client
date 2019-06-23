import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from enum import Enum

from gui_common import move_message_to_queue, update_tk, set_window_to_screen_center
from utils import create_handy_nursery


enable_text_autoscrolling = True


class ReadConnectionStateChanged(Enum):
    INITIATED = 'connection establishment...'
    ESTABLISHED = 'connection established'
    CLOSED = 'connection closed'

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(Enum):
    INITIATED = 'connection establishment...'
    ESTABLISHED = 'connection established'
    CLOSED = 'connection closed'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname


def disable_autoscrolling(event):
    global enable_text_autoscrolling
    enable_text_autoscrolling = False


def enable_autoscrolling(event):
    global enable_text_autoscrolling
    enable_text_autoscrolling = True


async def update_conversation_history(panel, messages_queue):
    while True:
        msg = await messages_queue.get()

        panel['state'] = 'normal'
        if panel.index('end-1c') != '1.0':
            panel.insert('end', '\n')
        panel.insert('end', msg)

        if enable_text_autoscrolling:
            panel.yview(tk.END)
        panel['state'] = 'disabled'


async def update_status_panel(status_labels, status_updates_queue):
    nickname_label, read_label, write_label = status_labels

    read_label['text'] = 'Reading: no connection'
    write_label['text'] = 'Sending: no connection'
    nickname_label['text'] = 'Username: unknown'

    while True:
        message = await status_updates_queue.get()

        if isinstance(message, ReadConnectionStateChanged):
            read_label['text'] = f'Reading: {message}'

        if isinstance(message, SendingConnectionStateChanged):
            write_label['text'] = f'Sending: {message}'

        if isinstance(message, NicknameReceived):
            nickname_label['text'] = f'Username: {message.nickname}'


def create_status_panel(root_frame):
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side='bottom', fill=tk.X)

    connections_frame = tk.Frame(status_frame)
    connections_frame.pack(side='left')

    nickname_label = tk.Label(
        connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    nickname_label.pack(side='top', fill=tk.X)

    status_read_label = tk.Label(
        connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    status_read_label.pack(side='top', fill=tk.X)

    status_write_label = tk.Label(
        connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    status_write_label.pack(side='top', fill=tk.X)

    return nickname_label, status_read_label, status_write_label


async def draw(messages_queue, sending_queue, status_updates_queue):
    root = tk.Tk()

    root.title('Minecraft Chat')

    root_frame = tk.Frame()
    root_frame.pack(fill='both', expand=True)

    status_labels = create_status_panel(root_frame)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side='bottom', fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side='left', fill=tk.X, expand=True)

    input_field.bind(
        '<Return>',
        lambda event: move_message_to_queue(input_field, sending_queue),
    )

    send_button = tk.Button(input_frame)
    send_button['text'] = 'Send'
    send_button['command'] = lambda: move_message_to_queue(input_field, sending_queue)
    send_button.pack(side='left')

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side='top', fill='both', expand=True)
    conversation_panel.vbar.bind('<Enter>', disable_autoscrolling)
    conversation_panel.vbar.bind('<Leave>', enable_autoscrolling)

    root.update_idletasks()

    set_window_to_screen_center(root)

    async with create_handy_nursery() as nursery:
        nursery.start_soon(
            update_tk(root_frame),
        )
        nursery.start_soon(
            update_conversation_history(conversation_panel, messages_queue),
        )
        nursery.start_soon(
            update_status_panel(status_labels, status_updates_queue),
        )

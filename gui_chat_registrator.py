import tkinter as tk

from gui_common import update_tk, set_window_to_screen_center
from utils import create_handy_nursery


def handle_register_button_click(button, nickname_input_field, nickname_queue):
    nickname = nickname_input_field.get()

    if nickname:
        nickname_queue.put_nowait(nickname)
        button['state'] = 'disabled'


async def handle_button_state(button, button_state_queue):
    while True:
        button['state'] = await button_state_queue.get()


async def draw(nickname_queue, register_button_state_queue):
    root = tk.Tk()

    root.title('Minecraft Chat Registrator')
    root.resizable(False, False)

    root_frame = tk.Frame()
    root_frame.pack(fill='both', expand=True)

    info_label = tk.Label(
        root_frame, height=2, width=30, fg='black', font='arial 14', anchor='w')
    info_label.pack(side='top', fill=tk.X, padx=10)
    info_label['text'] = 'Enter preferred nickname:'

    nickname_input_field = tk.Entry(root_frame, font='arial 18')
    nickname_input_field.pack(side='top', fill=tk.X, expand=True, padx=10)

    register_button = tk.Button(root_frame, font='arial 14', height=1)
    register_button['text'] = 'Register'
    register_button['command'] = lambda: handle_register_button_click(
        button=register_button,
        nickname_input_field=nickname_input_field,
        nickname_queue=nickname_queue,
    )
    register_button.pack(side='top', ipady=10, pady=10)

    root.update_idletasks()

    set_window_to_screen_center(root)

    async with create_handy_nursery() as nursery:
        nursery.start_soon(
            update_tk(
                root_frame=root_frame,
            ),
        )
        nursery.start_soon(
            handle_button_state(
                button=register_button,
                button_state_queue=register_button_state_queue,
            )
        )

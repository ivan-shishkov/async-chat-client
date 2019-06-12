import asyncio
import tkinter as tk


class TkAppClosed(Exception):
    pass


def add_message_to_queue(input_field, messages_queue):
    text = input_field.get()

    if text:
        messages_queue.put_nowait(text)
        input_field.delete(0, tk.END)


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


def get_window_size(window):
    geometry_info = window.geometry().split('+')
    size_info = geometry_info[0].split('x')
    window_width = int(size_info[0])
    window_height = int(size_info[1])

    return window_width, window_height


def set_window_to_center_screen(window):
    window_width, window_height = get_window_size(window)

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    window.geometry(
        f'+{screen_width // 2 - window_width // 2}'
        f'+{screen_height // 2 - window_height // 2}',
    )

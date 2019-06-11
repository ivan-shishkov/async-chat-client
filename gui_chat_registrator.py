import asyncio
import tkinter as tk


class TkAppClosed(Exception):
    pass


def process_nickname(input_field, sending_queue):
    text = input_field.get()

    if text:
        sending_queue.put_nowait(text)
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


async def draw(nickname_queue):
    root = tk.Tk()

    root.title('Minecraft Chat Registrator')
    root.resizable(False, False)

    root_frame = tk.Frame()
    root_frame.pack(fill='both', expand=True)

    info_label = tk.Label(
        root_frame, height=2, width=30, fg='black', font='arial 14', anchor='w')
    info_label.pack(side='top', fill=tk.X, padx=10)
    info_label['text'] = 'Enter preferred nickname:'

    input_field = tk.Entry(root_frame, font='arial 18')
    input_field.pack(side='top', fill=tk.X, expand=True, padx=10)

    send_button = tk.Button(root_frame, font='arial 14', height=1)
    send_button['text'] = 'Register'
    send_button['command'] = lambda: process_nickname(input_field, nickname_queue)
    send_button.pack(side='top', ipady=10, pady=10)

    root.update_idletasks()

    set_window_to_center_screen(root)

    await update_tk(root_frame)

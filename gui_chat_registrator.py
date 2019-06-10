import asyncio
import tkinter as tk


class TkAppClosed(Exception):
    pass


def process_new_message(input_field, sending_queue):
    text = input_field.get()

    if text:
        sending_queue.put_nowait(text)


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def draw(sending_queue):
    root = tk.Tk()

    root.title('Minecraft Chat Registrator')

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
    send_button['command'] = lambda: process_new_message(input_field, sending_queue)
    send_button.pack(side='top', ipady=10, pady=10)

    await update_tk(root_frame)

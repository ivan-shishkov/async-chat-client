import tkinter as tk

from gui_common import move_message_to_queue, update_tk, set_window_to_screen_center


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
    send_button['command'] = lambda: move_message_to_queue(input_field, nickname_queue)
    send_button.pack(side='top', ipady=10, pady=10)

    root.update_idletasks()

    set_window_to_screen_center(root)

    await update_tk(root_frame)

# Async Chat Client

This solution is a chat client that has a graphical user interface and uses the [asyncio](https://docs.python.org/3/library/asyncio.html) module for its work.

Main features:

* new user registration in chat
* user authentication in chat
* reading chat messages
* send chat messages
* automatic reconnection in case of disconnection
* writing chat messages to a text file

## How to install

For script to work, you need to install **Python 3.7** and then install all dependencies:

```bash

$ pip install -r requirements.txt

```

## Chat Registration Module

![Chat Registrator](screenshots/chat_registrator.jpg?raw=true "Chat Registrator")

This module allows you to register a new user in the chat and save the received authorization token in a text file.

### How to set up

```bash

$ python chat_registrator.py -h
usage: chat_registrator.py [-h] --host HOST [--port PORT] [--output OUTPUT]

If an arg is specified in more than one place, then commandline values
override environment variables which override defaults.

optional arguments:
  -h, --help       show this help message and exit
  --host HOST      Host for connect to chat. Required [env var: CHAT_HOST]
  --port PORT      Port for connect to chat. Default: 5050 [env var:
                   CHAT_WRITE_PORT]
  --output OUTPUT  Filepath for save user credentials. Default:
                   user_credentials.txt [env var:
                   USER_CREDENTIALS_OUTPUT_FILEPATH]

```

### How to launch

```bash

$ export CHAT_HOST='your.chat.host'
$ python chat_registrator.py

```

In the window that appears, you must enter your preferred nickname and click on the "Register" button. 
After successful registration, the token for authorization will be saved in a text file.

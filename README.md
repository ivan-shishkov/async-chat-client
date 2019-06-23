# Async Chat Client

This solution is a chat client that has a graphical user interface and uses the [asyncio](https://docs.python.org/3/library/asyncio.html) module for its work.

Main features:

* new user registration in chat with saving user credentials in a JSON file
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

This module allows you to register a new user in the chat and save the received user credentials in a JSON file.

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
                   user_credentials.json [env var: USER_CREDENTIALS_FILEPATH]

```

### How to launch

```bash

$ export CHAT_HOST='your.chat.host'
$ python chat_registrator.py

```

In the window that appears, you must enter your preferred nickname and click on the "Register" button. 
After successful registration, user credentials will be saved in a JSON file.

## Chat Client Module

![Chat Client](screenshots/chat_client.jpg?raw=true "Chat Client")

This module allows you to read and write messages in the chat with the pre-authorization of the user using the authorization token.

### How to set up

```bash

$ python chat_client.py -h
usage: chat_client.py [-h] --host HOST [--read-port READ_PORT]
                      [--write-port WRITE_PORT] [--credentials CREDENTIALS]
                      [--token TOKEN] [--output OUTPUT]

If an arg is specified in more than one place, then commandline values
override environment variables which override defaults.

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           Host for connect to chat. Required [env var:
                        CHAT_HOST]
  --read-port READ_PORT
                        Port for connect to chat for reading messages.
                        Default: 5000 [env var: CHAT_READ_PORT]
  --write-port WRITE_PORT
                        Port for connect to chat for writing messages.
                        Default: 5050 [env var: CHAT_WRITE_PORT]
  --credentials CREDENTIALS
                        Path to the file with user credentials. Default:
                        user_credentials.json [env var:
                        USER_CREDENTIALS_FILEPATH]
  --token TOKEN         User token for authorisation in chat. If given, then
                        auth token from file with user credentials will be
                        ignored [env var: CHAT_AUTH_TOKEN]
  --output OUTPUT       Filepath for save chat messages. Default: chat.txt
                        [env var: CHAT_MESSAGES_OUTPUT_FILEPATH]

```

### How to launch

```bash

$ export CHAT_HOST='your.chat.host'
$ python chat_client.py

```

# Project Goals

The code is written for educational purposes - this is a lesson in the course on Python and web development on the site [Devman](https://dvmn.org).
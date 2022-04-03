# Passport appointements checker for Paris

A tool to check and notify about available appointments for passports/CNI in Paris.  
It does not book slots for you.

Inspired by : https://github.com/nirae/42_slot_checker

## Usage

```
./src/passport_checker.py -h
usage: passport_checker.py [-h] [-c CONFIG] [-v]

Passport appointments checker for Paris

optional arguments:
  -h, --help                    show this help message and exit
  -c CONFIG, --config CONFIG    config file
  -v, --verbose                 include debugging logs
```

If you have missing dependencies, install them with pip:

```
pip install -r requirements.txt
```

or consider using a virtual environment (for instance with [pipenv](https://pypi.org/project/pipenv/) and similarly set it up from the requirements:

```
# Open a shell in the virtual env
pipenv shell
pipenv install
```

## Usage with Docker

Full set-up is provided with Docker, docker-compose and Makefile.  
If you don't have Docker and docker-compose, check out the official [Docker](https://docs.docker.com/get-docker/) and [Docker-Compose](https://docs.docker.com/compose/install/) doc and follow the guidelines for your distribution.

Then you can run one of the makefile rules:

```
# Build and up container
make up

# Build and up container in detached mode
make upd
```

## Configuration

The program work with a YAML configuration file, `config.yml` by default

### Minimal configuration

```yml
to_date: "30/06/2022"
refresh: 30
send:
  telegram:
    token: "000000000:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    chat_id: "0000000000"
```

### All options

```yml
from_date: ""
from_time: "06:00"
to_date: "30/06/2022"
to_time: "21:00"
person_number: 1
days:
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
  - 7
refresh: 30
send:
  telegram:
    token: '000000000:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    chat_id: '0000000000'

```

## Sending

To send with `telegram`, you need a bot. [How to create a telegram bot?](https://fr.jeffprod.com/blog/2017/creer-un-bot-telegram/)

:warning: Don't forget to talk to your bot one first time :warning:

You need the `token` of your bot, and **your** `chat_id`
To find your `chat_id`, initiate a conversation with the telegram bot @chatid_echo_bot

## Debug

Set the environment variable `SLOT_CHECKER_DEBUG` to get more detailed logs.

To get more detailed logs:

- with docker: set the environment variable `SLOT_CHECKER_DEBUG` in the docker-compose.yml
- without docker: run the slot_checker with its --verbose option.

## TODO

- [] add discord on senders
```

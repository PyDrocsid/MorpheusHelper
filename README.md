<p>

  [![CI](https://github.com/PyDrocsid/MorpheusHelper/actions/workflows/ci.yml/badge.svg)](https://github.com/PyDrocsid/MorpheusHelper/actions/workflows/ci.yml)
  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
  [![Maintainability](https://api.codeclimate.com/v1/badges/b0cfbebabf9129ae4335/maintainability)](https://codeclimate.com/github/PyDrocsid/MorpheusHelper/maintainability)
  [![Version](https://img.shields.io/github/v/tag/PyDrocsid/MorpheusHelper?label=version)](https://ghcr.io/pydrocsid/morpheushelper)
  [![Discord](https://img.shields.io/discord/637234990404599809.svg?label=Discord&logo=discord&logoColor=ffffff&color=7389D8)](https://pydrocsid.defelo.de/discord)
  [![Matrix](https://img.shields.io/matrix/pydrocsid:matrix.defelo.de.svg?label=Matrix&logo=matrix&logoColor=ffffff&color=4db798)](https://pydrocsid.defelo.de/matrix)

</p>

# MorpheusHelper
Bot for the [Discord Server of The Morpheus Tutorials](https://discord.gg/themorpheus)

## Development
### Prerequisites
- [Python 3.10](https://python.org/)
- [Poetry](https://python-poetry.org/) + [poethepoet](https://pypi.org/project/poethepoet/)
- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/) + [docker-compose](https://docs.docker.com/compose/) (recommended)
- [PyCharm Community/Professional](https://www.jetbrains.com/pycharm/) (recommended)

### Clone the repository

#### SSH (recommended)
```bash
git clone --recursive git@github.com:PyDrocsid/MorpheusHelper.git
```

#### HTTPS
```bash
git clone --recursive https://github.com/PyDrocsid/MorpheusHelper.git
```

### Setup development environment

After cloning the repository, you can setup the development environment by running the following command:

```bash
poe setup
```

This will create a virtual environment, install the dependencies, create a `.env` file and install the pre-commit hook.


### Environment variables
To set the required environment variables it is necessary to create a file named `.env` in the root directory (there is a template for this file in [`morpheushelper.env`](morpheushelper.env)). If you need a token, generate one by following these instructions: [Creating a Bot Account](https://docs.pycord.dev/en/master/discord.html) (Note you need to enable the options under `Privileged Gateway Intents`)

### Project structure

```
Project
├── bot
│  ├── cogs
│  │  ├── custom
│  │  │  ├── <cog>
│  │  │  │  ├── translations
│  │  │  │  │  └── en.yml
│  │  │  │  ├── __init__.py
│  │  │  │  ├── api.py
│  │  │  │  ├── cog.py
│  │  │  │  ├── colors.py
│  │  │  │  ├── models.py
│  │  │  │  ├── permissions.py
│  │  │  │  └── settings.py
│  │  │  ├── contributor.py
│  │  │  ├── pubsub.py
│  │  │  └── translations.py
│  │  └── library (submodule)
│  │     ├── <category>
│  │     │  └── <cog>
│  │     │     ├── translations
│  │     │     │  └── en.yml
│  │     │     ├── __init__.py
│  │     │     ├── api.py
│  │     │     ├── cog.py
│  │     │     ├── colors.py
│  │     │     ├── documentation.md
│  │     │     ├── models.py
│  │     │     ├── permissions.py
│  │     │     └── settings.py
│  │     ├── contributor.py
│  │     ├── pubsub.md
│  │     ├── pubsub.py
│  │     └── translations.py
│  ├── bot.py
│  └── morpheushelper.py
└── config.yml
```

### PyCharm configuration

- Open PyCharm and go to `Settings` ➔ `Project: MorpheusHelper` ➔ `Python Interpreter`
- Open the menu `Python Interpreter` and click on `Show All...`
- Click on the plus symbol
- Click on `Poetry Environment`
- Select `Existing environment` (setup the environment first by running `poe setup`)
- Confirm with `OK`
- Change the working directory to root path  ➔ `Edit Configurations`  ➔ `Working directory`


Finally, please remember to mark the `bot` directory as `Sources Root` (right click on `bot` ➔ `Mark Directory as` ➔ `Sources Root`).


## Installation instructions

### Using Docker
```bash
# clone git repository and cd into it
git clone --recursive https://github.com/PyDrocsid/MorpheusHelper.git
cd MorpheusHelper

# build docker image
sudo docker build -t pydrocsid/morpheushelper .

# adjust the docker-compose.yml and create a .env file
cp morpheushelper.env .env
vim .env
vim docker-compose.yml

# start redis, database and bot using docker-compose
sudo docker-compose up -d
```

### Local installation
```bash
# install poetry and poethepoet
pip install poetry poethepoet

# create virtual environment and install requirements
poetry install --no-root --no-dev

# start the bot
poe bot
```

### Environment variables
| Variable Name       | Description                                                                     | Default Value    |
|:--------------------|:--------------------------------------------------------------------------------|:-----------------|
| TOKEN               | Discord Bot Token                                                               |                  |
| GITHUB_TOKEN        | GitHub Personal Access Token (PAT) with public access                           |                  |
| LOG_LEVEL           | one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                          | `INFO`           |
| PYCORD_LOG_LEVEL    | one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                          | `ERROR`          |
|                     |                                                                                 |                  |
| DB_DRIVER           | Name of the SQL connection driver                                               | `mysql+aiomysql` |
| DB_HOST             | Hostname of the database server                                                 | `localhost`      |
| DB_PORT             | Port on which the database server is running                                    | `3306`           |
| DB_DATABASE         | Name of the database you want to use                                            | `bot`            |
| DB_USER             | Username for the database account                                               | `bot`            |
| DB_PASSWORD         | Password for the database account                                               | `bot`            |
| POOL_RECYCLE        | Number of seconds between db connection recycling                               | `300`            |
| POOL_SIZE           | Size of the connection pool                                                     | `20`             |
| MAX_OVERFLOW        | The maximum overflow size of the connection pool                                | `20`             |
| SQL_SHOW_STATEMENTS | whether SQL queries should be logged                                            | `False`          |
|                     |                                                                                 |                  |
| REDIS_HOST          | Hostname of the redis server                                                    | `redis`          |
| REDIS_PORT          | Port on which the redis server is running                                       | `6379`           |
| REDIS_DB            | Index of the redis database you want to use                                     | `0`              |
|                     |                                                                                 |                  |
| CACHE_TTL           | Time to live of redis cache in seconds                                          | `28800`          |
| RESPONSE_LINK_TTL   | Time to live of links between command messages and the resulting bot responses  | `7200`           |
|                     |                                                                                 |                  |
| REPLY               | wether to use the reply feature when responding to commands                     | `True`           |
| MENTION_AUTHOR      | wether to mention the author when the reply feature is being used               | `True`           |
|                     |                                                                                 |                  |
| SENTRY_DSN          | [Optional] Sentry DSN for logging                                               |                  |
| SENTRY_ENVIRONMENT  | [Optional] Sentry environment                                                   | `production`     |
| OWNER_ID            | [Optional] Discord User ID of the person who should recieve status information. |                  |
| DISABLED_COGS       | [Optional] Cogs you'd like to disable.                                          |                  |
|                     |                                                                                 |                  |

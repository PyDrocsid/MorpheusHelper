# PyDrocsid Bot Template

## Template Instructions
- [ ] Adjust name, repository and author in [config.yml](https://github.com/PyDrocsid/template/blob/develop/config.yml)
- [ ] Replace the banner in [bot/pydrocsid_bot.py#L19](https://github.com/PyDrocsid/template/blob/develop/bot/pydrocsid_bot.py#L19). You can generate one on [this website](http://www.patorjk.com/software/taag/#p=display&f=Slant&t=PyDrocsid%20Bot).
- [ ] Adjust repository in [Dockerfile#L21](https://github.com/PyDrocsid/template/blob/develop/Dockerfile#L21)
- [ ] Adjust docker image tags in [.github/workflows/ci.yml#L9](https://github.com/PyDrocsid/template/blob/develop/.github/workflows/ci.yml#L9)
- [ ] Enable push to docker registries in [.github/workflows/ci.yml#L158](https://github.com/PyDrocsid/template/blob/develop/.github/workflows/ci.yml#L158)
- [ ] Add reviewers in [.github/dependabot.yml](https://github.com/PyDrocsid/template/blob/develop/.github/dependabot.yaml)
- [ ] Adjust this [README.md](https://github.com/PyDrocsid/template/blob/develop/README.md) and remove this section

## Development
### Prerequisites
- [Python](https://python.org/) >=3.9
- [Pipenv](https://github.com/pypa/pipenv/)
- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/) (recommended)
- [docker-compose](https://docs.docker.com/compose/) (recommended)
- [PyCharm Community/Professional](https://www.jetbrains.com/pycharm/) (recommended)

### Clone the repository

#### SSH (recommended)
```
git clone --recursive git@github.com:PyDrocsid/template.git
```

#### HTTPS
```
git clone --recursive https://github.com/PyDrocsid/template.git
```

### Setup dependencies

After you have cloned the repository, you should create a virtual environment and install all dependencies. For this you can use the following command:

```
pipenv install --dev
```

### Environment variables
To set the required environment variables it is necessary to create a file named `.env` in the root directory (there is a template for this file in [`bot.env`](bot.env)). If you need a token, generate one by following these instructions: [Creating a Bot Account](https://discordpy.readthedocs.io/en/latest/discord.html) (Note you need to enable the options under `Privileged Gateway Intents`)

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
│  │     │     ├── models.py
│  │     │     ├── permissions.py
│  │     │     └── settings.py
│  │     ├── contributor.py
│  │     ├── pubsub.py
│  │     └── translations.py
│  ├── bot.py
│  └── pydrocsid_bot.py
└── config.yml
 ```

### PyCharm configuration

- Open PyCharm and go to `Settings` ➔ `Project` ➔ `Python Interpreter`
- Open the menu `Python Interpreter` and click on `Show All...`
- Click on the plus symbol
- Click on `Pipenv Environment`
- Select `Python 3.9` as `Base interpreter`
- Confirm with `OK`
- Change the working directory to root path  ➔ `Edit Configurations`  ➔ `Working directory`


Finally, please remember to mark the `bot` directory as `Sources Root` (right click on `bot` ➔ `Mark Directory as` ➔ `Sources Root`).


## Installation instructions

### Using Docker
```bash
# clone git repository and cd into it
git clone --recursive https://github.com/PyDrocsid/template.git
cd template

# build docker image
sudo docker build -t pydrocsid/bot .

# adjust the docker-compose.yml and create the .env file
cp bot.env .env
vim .env
vim docker-compose.yml

# start redis, database and bot using docker-compose
sudo docker-compose up -d
```

### Local installation
```bash
# install pipenv
pip install pipenv

# create virtual environment and install requirements
pipenv install

# start the bot
pipenv run bot
```

### Environment variables
|    Variable Name    |                                     Description                                      |  Default Value   |
|:--------------------|:-------------------------------------------------------------------------------------|:-----------------|
| TOKEN               | Discord Bot Token                                                                    |                  |
| GITHUB_TOKEN        | GitHub Personal Access Token (PAT) with public access                                |                  |
| LOG_LEVEL           | one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                               | `INFO`           |
|                     |                                                                                      |                  |
| DB_DRIVER           | Name of the SQL connection driver                                                    | `mysql+aiomysql` |
| DB_HOST             | Hostname of the database server                                                      | `localhost`      |
| DB_PORT             | Port on which the database server is running                                         | `3306`           |
| DB_DATABASE         | Name of the database you want to use                                                 | `bot`            |
| DB_USER             | Username for the database account                                                    | `bot`            |
| DB_PASSWORD         | Password for the database account                                                    | `bot`            |
| POOL_RECYCLE        | Number of seconds between db connection recycling                                    | `300`            |
| POOL_SIZE           | Size of the connection pool                                                          | `20`             |
| MAX_OVERFLOW        | The maximum overflow size of the connection pool                                     | `20`             |
| SQL_SHOW_STATEMENTS | whether SQL queries should be logged                                                 | `False`          |
|                     |                                                                                      |                  |
| REDIS_HOST          | Hostname of the redis server                                                         | `redis`          |
| REDIS_PORT          | Port on which the redis server is running                                            | `6379`           |
| REDIS_DB            | Index of the redis database you want to use                                          | `0`              |
|                     |                                                                                      |                  |
| CACHE_TTL           | Time to live of redis cache in seconds                                               | `28800`          |
| RESPONSE_LINK_TTL   | Time to live of links between command messages and the resulting bot responses       | `7200`           |
|                     |                                                                                      |                  |
| REPLY               | wether to use the reply feature when responding to commands                          | `True`           |
| MENTION_AUTHOR      | wether to mention the author when the reply feature is being used                    | `True`           |
|                     |                                                                                      |                  |
| SENTRY_DSN          | [Optional] Sentry DSN for logging                                                    |                  |
| OWNER_ID            | [Optional] Discord User ID of the person who should recieve status information.      |                  |
| DISABLED_COGS       | [Optional] Cogs you'd like to disable.                                               |                  |
|                     |                                                                                      |                  |
| AOC_SESSION         | [Optional] Session cookie of the [Advent of Code Website](https://adventofcode.com/) |                  |
| AOC_REFRESH_INTERVAL| [Optional] Number of seconds after which the aoc cache is invalidated                | `900`            |

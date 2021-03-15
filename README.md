# MorpheusHelper
Bot for the [Discord Server of The Morpheus Tutorials](https://discord.gg/themorpheus)

## Development
### Prerequisites
- [Python](https://python.org/) >=3.9
- [Pipenv](https://github.com/pypa/pipenv/)
- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/) (recommended)
- [docker-compose](https://docs.docker.com/compose/) (recommended)
- [PyCharm Community/Professional](https://www.jetbrains.com/pycharm/) (recommended)

### Setup dependencies

After you have cloned the repository, you should create a virtual environment and install all dependencies. For this you can use the following command:

```
pipenv install --dev
```

### Environment variables 
To set the required environment variables it is necessary to create a file named `.env` in the root directory. If you need a token, generate one by following these instructions: [Creating a Bot Account](https://discordpy.readthedocs.io/en/latest/discord.html) (Note you need to enable the options under `Privileged Gateway Intents`)

```
TOKEN=xxx
```

### Project structure 

Inside the project you can find all bot features (like the mod tools) in the `cogs` directory. 
The database is represented by the models, which can be found in the `models` directory. 
For translations we use a `.yml` file which can be found in the `translations` directory.

```
Project
│
└───morpheushelper  
│   └───cogs
│   │    │   adventofcode.py
│   │    │   automod.py
│   │        ...
|   |
│   └───models
│        │   allowed_invite.py
│        │   aoc_link.py
│            ...
|
└───translations
    │   en.yml
        ...
```

### PyCharm configuration 

- Open PyCharm and go to `Settings` ➔ `Project: MorpheusHelper` ➔ `Python Interpreter`
- Open the menu `Python Interpreter` and click on `Show All...`
- Click on the plus symbol 
- Click on `Pipenv Environment`
- Select `Python 3.9` as `Base interpreter`
- Confirm with `OK`

Finally, please remember to mark the `morpheushelper` directory as `Sources Root` (right click on `morpheushelper` ➔ `Mark Directory as` ➔ `Sources Root`).


## Installation instructions

### using docker
```bash
# clone git repository
git clone https://github.com/Defelo/MorpheusHelper

# build docker image
sudo docker build -t defelo/morpheushelper MorpheusHelper

# adjust the docker-compose.yml file (e.g. with your discord token)
vim MorpheusHelper/docker-compose.yml

# start database and bot using docker-compose
sudo docker-compose -f MorpheusHelper/docker-compose.yml up -d
```

### local installation
```bash
# install pipenv
pip3 install pipenv

# create virtual environment and install requirements
pipenv install

# start the bot
pipenv run bot
```

### Environment variables
| Variable Name |                                   Description                                   | Default Value |
|:--------------|:--------------------------------------------------------------------------------|:--------------|
| TOKEN         | Discord Bot Token                                                               |               |
| DB_HOST       | Hostname of the database server                                                 | localhost     |
| DB_PORT       | Port on which the database server is running                                    | 3306          |
| DB_DATABASE   | Name of the database in which morpheushelper should store data.                 | test          |
| DB_USER       | Username for the database account                                               | test          |
| DB_PASSWORD   | Password for the database account                                               | test          |
| GITHUB_TOKEN  | GitHub Personal Access Token (PAT) with public access                           |               |
| SENTRY_DSN    | [Optional] Sentry DSN for logging                                               |               |
| OWNER_ID      | [Optional] Discord User ID of the person who should recieve status information. |               |
| DISABLED_COGS | [Optional] Cogs you'd like to disable.                                          |               |
| AOC_SESSION   | [Optional] Session cookie of the AOC Website                                    |               |

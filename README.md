# Documentation

## Development
### Prerequisites
- [Python](https://python.org/) >=3.9
- [Pipenv](https://github.com/pypa/pipenv/)
- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/) (recommended)
- [PyCharm Community/Professional](https://www.jetbrains.com/pycharm/) (recommended)

### Setup dependencies

After you have cloned the repository you should create a virtual environment and install all dependencies. For this you can use the following command:

```
pipenv install --dev
```

### Environment variables 
To use the required environment variables it is necessary to create a file named `.env` in the root directory. If you need a token generate one by following these instructions [Creating a Bot Account](https://discordpy.readthedocs.io/en/latest/discord.html).(Note you need to enable the options under Privileged Gateway Intents)

```
TOKEN=xxx
```

### Project structure 

Inside the project you can find all bot commands like the modtools in the directory `cogs`. 
The database is represented by the models, which can be found in the `models` directory. 
For translations we use a `.yml` file which can be found in the translations `directory`.

### PyCharm configuration 

* Open Pycharm and go to Settings/Python Interpreter
* Open the Menu Pyton Interpreter and click on Show All...
* Click on the plus symbol 
* Click left on Pipenv Enviorment
* Set Python3.9 on Base interpreter 
* Confirm with OK

Finally, please remember to mark the morpheushelper directory as Sources Root. You can do this with a right click on the folder name  


## Installation instructions

### using docker
```bash
# clone git repository
git clone https://github.com/Defelo/MorpheusHelper

# build docker image
docker build -t defelo/morpheushelper MorpheusHelper

# adjust the docker-compose.yml file (e.g. with your discord token)
vim MorpheusHelper/docker-compose.yml

# start database and bot using docker-compose
docker-compose -f MorpheusHelper/docker-compose.yml up -d
```

### local installation
```bash
# install pipenv
pip3 install pipenv

# create venv and install requirements
pipenv install

# start the bot
pipenv run bot
```

### Environment variables
| Variable Name |                                   Description                                   | Default Value |
|:-------------:|:-------------------------------------------------------------------------------:|:-------------:|
| TOKEN         | Discord Bot Token                                                               |               |
| DB_HOST       | Hostname of the database server                                                 | localhost     |
| DB_PORT       | Port on which the database server is running                                    | 3306          |
| DB_DATABASE   | Name of the database in which morpheushelper should store data.                 | test          |
| DB_USER       | Username for the database account                                               | test          |
| DB_PASSWORD   | Password for the database account                                               | test          |
| SENTRY_DSN    | [Optional] Sentry DSN for logging                                               |               |
| OWNER_ID      | [Optional] Discord User ID of the person who should recieve status information. |               |
| DISABLED_COGS | [Optional] Cogs you'd like to disable.                                          |               |
| AOC_SESSION   | [Optional] Session cookie of the AOC Website                                    |               |




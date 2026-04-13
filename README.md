# Flytwo
Flyone client to get the cheapest flights

# Usage

python3.13 or higher is required

`uv tool install -e .`

`flytwo flights --origin RMO --destination EVN --currency EUR --travel_date 2024-12-01`

# For devs

### Install dependencies
`uv sync --dev`

### Configure environment (preferably use .env file)

```
BOT_TOKEN=<your bot token (obtained from @BotFather)>

DB_HOST=localhost
DB_NAME=flytwo
DB_PORT=5432
DB_USER=flytwo
DB_PASS=<your password goes here>
```

In this configuration redis cache will not work as well as /go command. But should be fine for most of the tasks.

### Project structure

```
.
├── Makefile <main commands to build project, set hooks, create db migrations>
├── migrations <alembic migrations, represent changes in database> 
├── src
│   ├── bot.py <project's frontend>
│   ├── ... <every other file relates to project backend parts and has descriptive name>
│   ├── fly_client <standalone cli app and library that handles connections to flyone>
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   └── client.py
│   ├── task_<name>.py <peridict tasks that run on background and are triggered by schedule start with task_ prefix>
├── tests <autotests using pytest framework>

```

### Quick start

Working directory `~/flytwo/src`

Run bot (frontend) `python -m bot.bot`

Run notification task (backend) `python task_notify.py`

### Deployment

#### Standalone (includes its own postgres and redis)
```
docker compose -f docker-compose.yml up -d
```

#### Shared (reuses existing postgres and redis from another compose project)

First time only — create the shared network and attach existing services to it:
```
docker network create shared
docker network connect shared <postgres-container-name>
docker network connect shared <redis-container-name>
```

Set `DB_HOST` and `REDIS_HOST` in `.env` to the container names above, then:
```
docker compose -f compose-shared.yml up -d
```

Replace `<domain>` in `nginx.flytwo.conf` with your domain before starting.

### Guidelines

The code should comply with [PEP8](https://peps.python.org/pep-0008/)

Every new feature or bugfix should be covered with autotests to ensure it is working properly.

Submit PR's for code review when all current tests are PASSED.

Use English language in comments and '' instead of "" in strings.

Typehints, docstrings and even doctests are welcome.

Don't write comments if they are useless.

Try to avoid code duplication.

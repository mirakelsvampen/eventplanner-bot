eventplanner-bot
=========

A simple bot creating upcoming events and allows users to sign-up to lobby like structures.
The bot is commanded with text chat and also performs some background tasks such as cleaning invalid lobbies

Requirements
------------

This runs on Python version 3.9 and depends on the following libraries:

```python
discord.py
mysqlclient
sqlalchemy
sqlalchemy-utils
```

They are all included in the requirements.txt file and you can install then with `python3 -m pip install -r requirements.txt`.

**Required services**
* Mysql database - You need a mysql database available, this is used to store all members, lobbies and paricipant information.

Installation
--------------

A description of the settable variables for this role should go here, including any variables that are in defaults/main.yml, vars/main.yml, and any variables that can/should be set via parameters to the role. Any variables that are read from other roles and/or the global scope (ie. hostvars, group vars, etc.) should be mentioned here as well.

To simply run this bot you can execute `./main.py` after editing the `settings.json` file according to your settings. Take a look at the following example for configuring settings:

```jsonc
{   
    "client": {// app settings which can be acquired on the developer discord homepage
        "id": "",
        "secret": "",
        "bot_token": ""
    },
    "database": {
        "ip": "database", // can be a hostname, which is pretty handy when running docker
        "user": "root", // username for database access
        "password": "Syp9393", // password for aforementioned user
        "port": "3306" // port which mysql is listening on
    }
}
```

## Future plans

Since this project in work in progress there are many future plans; the following list shows everything that comes to mind.

*  Automatically clean up lobbies which are older than X days.
*  Add leader promotion
*  Add kick member support
*  Maybe use it for some python/javascript fullstack projects since the database structure is noob friendly
from dotenv import load_dotenv

load_dotenv(verbose=True)

from flask_script import Manager, Server
from flask_migrate import Migrate, MigrateCommand

from app import app
from app.models import db

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command("db", MigrateCommand)
manager.add_command("runserver", Server())

if __name__ == "__main__":
    manager.run()

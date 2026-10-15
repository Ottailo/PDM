from app import create_app, db
from flask_migrate import Migrate

app = create_app()

if __name__ == '__main__':
    # This script is intended to be used with flask command
    # flask --app manage:app db migrate
    pass

"""
Root Entrypoint for Vercel Python Framework Preset
"""
from api.index import app, application

if __name__ == '__main__':
    from api.index import flask_app
    if flask_app:
        flask_app.run()

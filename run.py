"""Legacy launch name redirects to the secure, explicitly configured pilot.

No simulator, online learning, global warning suppression or SocketIO startup.
Use the approved Browser preview configuration in development and wsgi:app in
production. The factory fails closed without required pilot configuration.
"""
import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    if app.config['APP_ENV'] != 'development':
        raise SystemExit('Use a production WSGI server for non-development environments.')
    app.run(host='127.0.0.1', port=int(os.environ.get('PILOT_PORT', '5051')), debug=False, use_reloader=False)

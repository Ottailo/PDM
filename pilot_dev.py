"""Run the local pilot API from its explicit, ignored configuration.

Launch with the Browser preview tool. Never imports the old simulator runner.
"""
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env.pilot', override=False)

from app import create_app

application = create_app()

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=int(os.environ.get('PILOT_PORT', '5051')), debug=False, use_reloader=False)

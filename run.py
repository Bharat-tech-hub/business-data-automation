"""Launch the dashboard: python run.py"""

import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent / "app" / "streamlit_app.py"

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(APP)]))

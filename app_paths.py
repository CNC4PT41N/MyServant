"""Keep editable files beside the executable in portable builds."""
import sys
from pathlib import Path

ROOT = (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False)
        else Path(__file__).resolve().parent)

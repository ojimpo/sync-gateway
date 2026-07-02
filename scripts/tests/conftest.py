"""scripts/ 配下の同期スクリプトを import できるように sys.path を通す。"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

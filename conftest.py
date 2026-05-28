"""pytest が admin パッケージを import できるよう、リポジトリルートを sys.path に追加。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

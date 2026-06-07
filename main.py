"""BehVault — 基于行为口令与国密SM4的智能保密文件库.

Entry point for the application.
"""

import sys
import os

# Ensure src is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import App


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()

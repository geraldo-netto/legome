"""Enable `python3 -m legome ...` invocation."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())

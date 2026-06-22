"""Enable `python -m ghostcorp ...`."""

import sys

from ghostcorp.cli import main

if __name__ == "__main__":
    sys.exit(main())

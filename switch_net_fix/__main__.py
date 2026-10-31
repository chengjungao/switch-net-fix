"""支持 ``python -m switch_net_fix``。"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())

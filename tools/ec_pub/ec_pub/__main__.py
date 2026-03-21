"""Allow running ec_pub as a module: python -m ec_pub"""

import sys
from ec_pub.main import main

sys.exit(main())

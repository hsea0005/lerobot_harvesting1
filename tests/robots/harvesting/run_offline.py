"""Execute the same tests against bundled LeRobot source with external import substitutes."""

import sys
import unittest
from pathlib import Path

from offline_bootstrap import install

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "src"))
install()
print("OFFLINE MOCK MODE: real bundled LeRobot classes/factories; external dependency imports substituted.")
print("Does not test real CLI decoding, serial packets, training, policy inference or physical motors.")
suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)

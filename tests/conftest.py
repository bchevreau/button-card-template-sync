"""Test helpers for loading the integration without Home Assistant."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

PACKAGE_NAME = "button_card_template_sync"
PACKAGE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "button_card_template_sync"
)


package = ModuleType(PACKAGE_NAME)
package.__path__ = [str(PACKAGE_PATH)]
sys.modules.setdefault(PACKAGE_NAME, package)

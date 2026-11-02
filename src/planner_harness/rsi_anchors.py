"""Compatibility alias; implementation lives in planner_harness.compat.rsi.rsi_anchors."""
from importlib import import_module as _import_module
import sys as _sys

_sys.modules[__name__] = _import_module("planner_harness.compat.rsi.rsi_anchors")

"""LMLM Secure Lifecycle Control (LSLC).

LSLC coordinates safe, offline preflight checks. It is not an OS sandbox and
must not be represented as one.
"""
from .runner import LifecycleReport, run_security_self_test

__all__ = ["LifecycleReport", "run_security_self_test"]

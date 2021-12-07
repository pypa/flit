"""A lil' TOML parser."""

__all__ = ("loads", "load", "TOMLDecodeError")
__version__ = "1.2.2"  # DO NOT EDIT THIS LINE MANUALLY. LET bump2version UTILITY DO IT

from flit_core._vendor.tomli._parser import TOMLDecodeError, load, loads

# Pretend this exception was created here.
TOMLDecodeError.__module__ = "tomli"

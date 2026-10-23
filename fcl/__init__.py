"""Functional Constraints Logic (FCL): parsing and online monitoring of temporal constraints.

See README.md in this folder for the syntax, semantics and API.
"""
from fcl.monitor import Formula, Monitor, State, Violation
from fcl.parser import parse

__all__ = ["parse", "Monitor", "Violation", "Formula", "State"]

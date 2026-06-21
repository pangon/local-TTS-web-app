"""Standalone operator scripts (NOT part of the product runtime).

Modules in this subpackage are manual command-line tools run by the operator
on the GPU host (e.g. building precomputed voice-clone prompts). They are
intentionally **not** imported by the FastAPI app, the API layer, or the
frontend (DEC-voice-clone-prompts) — keeping the request/synthesis path free of
the heavy, one-off model operations these tools perform.
"""

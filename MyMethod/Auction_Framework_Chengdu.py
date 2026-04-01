"""Deprecated compatibility wrapper for the old Chengdu auction experiment entrypoint."""

from __future__ import annotations

from capa.experiments import main


if __name__ == "__main__":
    raise SystemExit(main())

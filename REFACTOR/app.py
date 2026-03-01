import os
import sys


def _resolve_safe_main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from runtime import safe_main as _safe_main
    return _safe_main


def main():
    _resolve_safe_main()()


if __name__ == "__main__":
    main()
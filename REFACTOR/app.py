if __package__:
    from .runtime import safe_main
else:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from REFACTOR.runtime import safe_main

if __name__ == "__main__":
    safe_main()

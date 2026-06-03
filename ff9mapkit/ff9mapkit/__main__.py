"""Enable ``python -m ff9mapkit ...`` (identical to the ``ff9mapkit`` console command).

Handy when the package isn't pip-installed on PATH — run it from the repo:
    py -m ff9mapkit build my_room.field.toml --out dist
"""

from .cli import main

if __name__ == "__main__":
    main()

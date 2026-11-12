"""Confirm that every project library imports, and print its version."""

import importlib
import sys

LIBRARIES = [
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "plotly",
    "streamlit",
    "openpyxl",
    "xlsxwriter",
    "reportlab",
    "pytest",
]


def main() -> int:
    print(f"Python {sys.version.split()[0]} at {sys.executable}\n")
    failures = []
    for name in LIBRARIES:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "version attribute not found")
            print(f"OK    {name:<12} {version}")
        except Exception as exc:  # report any import problem, not only ImportError
            print(f"FAIL  {name:<12} {type(exc).__name__}: {exc}")
            failures.append(name)
    print()
    if failures:
        print(f"{len(failures)} librar{'y' if len(failures) == 1 else 'ies'} failed: {', '.join(failures)}")
        return 1
    print("All libraries imported successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

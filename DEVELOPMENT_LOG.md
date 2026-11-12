# Development Log

## Milestone 1: Environment and Project Initialization (in progress)

**Date started:** 2026-11-10

### Completed
- Windows 11, PowerShell, VS Code.
- Python 3.12.10 virtual environment (`.venv`). Python 3.14.2 remains the system default; not used because of library wheel risk.
- Git 2.56.0.4 installed. pip upgraded to 26.3.
- Folder structure created per the project brief; `.gitkeep` placeholders added.
- `.gitignore` created.
- Libraries installed and import-verified: pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, seaborn 0.13.2, plotly 7.1.0, streamlit 1.67.0, openpyxl 3.1.5, xlsxwriter 3.3.1, reportlab 5.1.0, pytest 9.2.0.
- `requirements.txt` pinned (51 lines, UTF-8) and confirmed with `pip install -r`.

### Decisions
- Local root folder is `D:\Python-Business-Development` (local naming change from `business-data-automation/`).
- Public GitHub repo under Bharat-tech-hub.
- No libraries outside the approved stack. Plotly charts stay in the dashboard; PDF charts use Matplotlib/Seaborn.
- `verify_environment.py` kept at the root as a temporary utility until Milestone 13.

### Known issues (fixed)
- PowerShell execution policy blocked venv activation; set to RemoteSigned for the current user.
- `requirements.txt` was first frozen before verification and was re-frozen as UTF-8 afterwards.

### Pending
- Git identity (email), first commit, GitHub remote.
- LICENSE decision.

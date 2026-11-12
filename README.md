# Python-Based Business Data Analysis & Automated Reporting System

A modular Python application that ingests business sales data (CSV/Excel), validates and cleans it, computes business KPIs, and produces interactive dashboards plus downloadable Excel and PDF reports.

**Status:** under development (Milestone 1: environment setup).

## Requirements

- Python 3.12
- Git

## Setup (Windows, PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python verify_environment.py
```

## Dataset

UCI Online Retail dataset: https://archive.ics.uci.edu/dataset/352/online+retail
Place the downloaded file in `data/raw/` (not committed to Git).

More documentation (business rules, architecture, usage) will be added as the project progresses.

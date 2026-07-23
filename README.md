# Mobility TCS Lab Experiment

If you use this code, please cite: 

_Guggenberger, Julia Anna and Seshadri, Ravi and Ciuffo, Biagio and Azevedo, Carlos Lima, Market Behavior in a Tradable Credit Scheme for Sustainable Mobility: Insights from a Lab Experiment. Available at SSRN: https://ssrn.com/abstract=6598859 or http://dx.doi.org/10.2139/ssrn.6598859_

## About

This repository contains the oTree implementation of a lab experiment studying
market behavior in a digital Tradable Credit Scheme (TCS) for sustainable mobility.
Participants make repeated daily commuting decisions (Travel Choice pages) and can
trade tokens in a central credit market (Market page) across a sequence of test
phases and three main phases (reduced allocation, cost variation, distance-based
allocation). Choice sets are built from participants' own real commuting data
(pre-survey + travel diary), so decisions reflect realistic, context-aware travel
behavior rather than abstract scenarios.

## Note on data

`choice_set.csv` and the map files under `static/maps/` included here are
**example/dummy data only**. The actual choice sets and maps are generated per
participant from the pre-survey and travel diary responses.

### 1. Clone the repository
```bash
git clone https://github.com/JuliaGuggenberger/mobilityTCS_experiment.git
cd mobilityTCS_experiment
```

### 2. Create a virtual environment
```bash
python3 -m venv venv_otree
```

### 3. Activate the virtual environment
**Mac/Linux:**
```bash
source venv_otree/bin/activate
```
**Windows (PowerShell):**
```powershell
venv_otree\Scripts\Activate.ps1
```
If you get an execution policy error on Windows, run this once first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

You should see `(venv_otree)` at the start of your terminal prompt once it's active.

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Start the app
```bash
otree devserver
```

Then open **http://localhost:8000** in your browser.

## Notes
- Make sure the Python version matches the one in `python-version` before creating the virtual environment.
- Always activate the virtual environment (step 3) before running any `otree` command.
- To stop the server, press `Ctrl+C` in the terminal.

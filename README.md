# Mobility TCS Experiment

An oTree experiment.

## Setup

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
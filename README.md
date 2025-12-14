# Poland procurement analysis script

This script is used to analyze procurement documents from the Polish government's procurement platform (https://ezamowienia.gov.pl/).

You run 3 scripts to execute the workflow:
* Initially you set the environment variables in `.env` file.
    - `KEYWORD`: The keyword to search for in the procurement documents. I used "uliczne" as an example, since it means street in poland and likely will return procurements related to street lighting.
    - `DATE`: The date to search for in the procurement documents. Use the date in the format `YYYY-MM-DD`. This is the initiation date of the procurement. Can be set to yesterday/today to query procuremnts daily.

* Afterwards script finds the procurements matching the keyword/date in `.env` file.
    - returns found procurements in `procurement_results.json`

* Then script downloads documents locally for the found procurements.
    - downloads documents to `downloads/` directory
    - creates a folder for each procurement
    - downloads all documents for each procurement

* Finally script analyzes the downloaded documents using OpenAI.
    - analyzes documents and returns results in `responses/` directory
    - creates a folder for each procurement
    - returns results in `responses/` directory

### Scripts that must be run consecutively:
- `find_procurements.py`: Finds procurements matching the keyword/date in `.env`.
- `download_docs.py`: Downloads documents locally for the found procurements.
- `analyze.py`: Analyzes the downloaded documents using OpenAI.

## Requirements
- Python 3.14
- OpenAI API key defined in `.env`

## Setup & Run

1. **Create Virtual Environment**:
   ```powershell
   py -m venv venv
   ```

2. **Install Dependencies**:
   It is easiest to use the full path to the virtual environment's pip:
   ```powershell
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. **Run Scripts**:
   You can run the scripts using the virtual environment's python directly:
   
   ```powershell
   .\venv\Scripts\python.exe find_procurements.py
   .\venv\Scripts\python.exe download_docs.py
   .\venv\Scripts\python.exe analyze.py
   ```

   *Alternatively, activate the environment first:*
   ```powershell
   .\venv\Scripts\Activate
   python analyze.py
   ```

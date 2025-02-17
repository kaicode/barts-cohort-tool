# Cohort Definition Builder


## Prerequisites
- Python 3.x installed
- `pip` and `virtualenv` or `venv` available

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```
   
2. Create the virtual environment
    ```bash
    python -m venv .venv
    ```

3. Activate the virtual environment:

    **__Linux/MacOS:__**
    ```bash
    source .venv/bin/activate
    ```
    **Windows:**
    ```bash
    .venv\Scripts\activate
    ```

4. Install dependencies:
    ```bash
    pip install -r requirements.txt
   ```

5. Run the application:
    ```bash
    uvicorn app.main:app --reload
    ```

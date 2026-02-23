# W40K SV Ranking - Backend API

This repository contains the backend engine for the Warhammer 40k Ranking System. It serves as a bridge between a private **Google Sheets** database and the Vue.js frontend, providing a clean REST API using **FastAPI**.

## Technologies
* **Python 3.10+**
* **FastAPI**: Modern, high-performance web framework for building APIs.
* **Gspread & OAuth2Client**: For secure Google Drive and Sheets API integration.
* **Pandas**: For data manipulation and JSON structuring.
* **Uvicorn**: Lightning-fast ASGI server implementation.

## Project Structure
```text
backend/
├── main.py              # FastAPI application logic
├── credenciales.json    # Google Service Account Key (IGNORED BY GIT)
├── requirements.txt     # Project dependencies
└── README.md            # Backend documentation
└── requirements.txt     # Backend requirements

Setup & Installation

Clone the repository:

Bash
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd backend
Create and activate a Virtual Environment:

Bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

Install Dependencies:

Bash
pip install fastapi uvicorn gspread oauth2client pandas

Google Cloud Configuration:

Place your credenciales.json file in the backend/ directory.

Ensure your Google Sheet is shared with the client_email found in your JSON credentials with Editor or Viewer permissions.

🏁 Running the Application
To start the development server with auto-reload:

Bash
python -m uvicorn main:app --reload
The API will be available at: http://127.0.0.1:8000

📊 API Endpoints
Get Full Ranking
Endpoint: GET /api/ranking

Description: Fetches all rows from the linked Google Sheet and returns them as a structured JSON array.

Response Example:

JSON
[
  {
    "Player": "BattleBrother01",
    "Faction": "Adeptus Militarum",
    "Wins": 10,
    "Losses": 2
  }
]

🛡️ Security Note
The credenciales.json file contains sensitive information and is excluded from version control via .gitignore.
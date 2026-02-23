from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os

app = FastAPI()

# Configuración de CORS: Autorizando frontend en Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "https://ranking-w40-ksv.vercel.app",
        "https://rankingw40ksv.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_google_sheet_data():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    try:
        google_creds_json = os.getenv("GOOGLE_SHEETS_CREDS")
        
        if google_creds_json:
            creds_dict = json.loads(google_creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif os.path.exists("credenciales.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        else:
            return None

        client = gspread.authorize(creds)
        spreadsheet = client.open("Kill Team SV Backup 4-3-25")
        sheet = spreadsheet.worksheet("Catalogos")

        values = sheet.get_all_values()
        if not values or len(values) < 1:
            return pd.DataFrame()

        df = pd.DataFrame(values[1:], columns=values[0])
        
        df = df.loc[:, df.columns != '']
        df = df.loc[:, ~df.columns.duplicated()]

        return df

    except Exception as e:
        print(f"ERROR: {e}")
        return None

@app.get("/")
def read_root():
    return {"status": "W40K Ranking API is Online"}

@app.get("/api/ranking")
async def get_ranking():
    df = get_google_sheet_data()
    if df is None:
        return {"error": "Error interno al conectar con Google Sheets"}
    if df.empty:
        return {"error": "La hoja está vacía"}
    return df.to_dict(orient="records")

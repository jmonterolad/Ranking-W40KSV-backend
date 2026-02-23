from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os
import uvicorn

app = FastAPI()

# Configuración de CORS habilitada para local y producción
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

RANKINGS_CONFIG = {
    "kt2025": {
        "file": "Kill Team SV Backup 4-3-25",
        "sheet": "Catalogos"
    },
    "kt2026": {
        "file": "Kill Team - Ranking SV 2026",
        "sheet": "Catalogos"
    },
    "40k1k2026": {
        "file": "Copia de 40K - 1KP Ranking SV 2026",
        "sheet": "Catalogos"
    }
}

def get_google_sheet_data(game_id: str):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    try:
        config = RANKINGS_CONFIG.get(game_id)
        if not config:
            print(f"ERROR: No hay configuración para el ID {game_id}")
            return None

        # Intenta cargar desde variable de entorno (Vercel) o archivo local (PC)
        google_creds_json = os.getenv("GOOGLE_SHEETS_CREDS")
        if google_creds_json:
            creds_dict = json.loads(google_creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif os.path.exists("credenciales.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        else:
            print("ERROR: No se encontró archivo de credenciales.")
            return None

        client = gspread.authorize(creds)
        spreadsheet = client.open(config["file"])
        sheet = spreadsheet.worksheet(config["sheet"])

        values = sheet.get_all_values()
        if not values or len(values) < 1:
            return pd.DataFrame()

        df = pd.DataFrame(values[1:], columns=values[0])
        df = df.loc[:, df.columns != '']
        df = df.loc[:, ~df.columns.duplicated()]

        return df

    except Exception as e:
        print(f"ERROR en get_google_sheet_data: {e}")
        return None

@app.get("/")
def read_root():
    return {"status": "W40K Ranking API is Online"}

@app.get("/api/ranking/{game_id}")
async def get_ranking(game_id: str):
    if game_id not in RANKINGS_CONFIG:
        return {"error": f"El ranking '{game_id}' no está configurado."}

    df = get_google_sheet_data(game_id)
    
    if df is None:
        return {"error": "Error de conexión con Google Sheets. Revisa permisos del archivo."}
    
    if df.empty:
        return {"error": "La hoja de datos está vacía."}
        
    return df.to_dict(orient="records")

# Bloque para ejecución local
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
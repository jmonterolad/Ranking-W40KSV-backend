from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import uvicorn
import os

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
        if not os.path.exists("credenciales.json"):
            print("ERROR: El archivo 'credenciales.json' no se encuentra.")
            return None

        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        client = gspread.authorize(creds)

        spreadsheet = client.open("Kill Team SV Backup 4-3-25")
        sheet = spreadsheet.worksheet("Catalogos")

        values = sheet.get_all_values()

        if not values or len(values) < 1:
            return pd.DataFrame()

        headers = values[0]
        data = values[1:]
        
        df = pd.DataFrame(data, columns=headers)

        df = df.loc[:, df.columns != '']
        
        df = df.loc[:, ~df.columns.duplicated()]

        print(f"DEBUG: Conexión exitosa. Filas procesadas: {len(df)}")
        return df

    except gspread.exceptions.SpreadsheetNotFound:
        print("ERROR: No se encontró el Google Sheet 'Kill Team SV Backup 4-3-25'.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        print("ERROR: La pestaña 'Catalogos' no existe.")
        return None
    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        return None


@app.get("/api/ranking")
async def get_ranking():
    df = get_google_sheet_data()

    if df is None:
        return {"error": "Error interno al conectar con Google Sheets"}

    if df.empty:
        return {"error": "La hoja 'Catalogos' está vacía o tiene un formato inválido"}

    # Conversion a JSON para el Frontend
    return df.to_dict(orient="records")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
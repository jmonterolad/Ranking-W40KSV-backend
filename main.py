from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import uvicorn

app = FastAPI()

# Configuracion de CORS para que tu Vue.js (puerto 5173) pueda comunicarse con FastAPI
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
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("Kill Team SV Backup 4-3-25").worksheet("Log de Batalla")
        
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error detallado: {e}")
        return None

@app.get("/api/ranking")
async def get_ranking():
    df = get_google_sheet_data()
    
    if df is None or df.empty:
        return {"error": "No se pudieron obtener los datos o la hoja está vacía"}
    
    # Convertimos el DataFrame de Pandas a una lista de diccionarios (JSON)
    return df.to_dict(orient="records")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
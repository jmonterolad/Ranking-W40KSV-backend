from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os
import uvicorn
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore
from datetime import datetime

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
        "file": "40K - 1KP Ranking SV 2026",
        "sheet": "Catalogos"
    }
}

# --- INICIALIZACIÓN DE FIREBASE ADMIN ---
try:
    if not firebase_admin._apps:
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_firebase = os.path.join(directorio_actual, "firebase-adminsdk.json")
        
        firebase_creds_json = os.getenv("FIREBASE_CREDS")
        
        if firebase_creds_json:
            cred = credentials.Certificate(json.loads(firebase_creds_json))
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin inicializado desde variable de entorno.")
        elif os.path.exists(ruta_firebase):
            cred = credentials.Certificate(ruta_firebase)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase Admin inicializado correctamente desde: {ruta_firebase}")
        else:
            print(f"❌ PELIGRO: No encuentro el archivo de Firebase exactamente en esta ruta: {ruta_firebase}")
except Exception as e:
    print(f"❌ ERROR FATAL inicializando Firebase: {e}")

# --- SISTEMA DE DEFENSA (Validación de Tokens) ---
security = HTTPBearer()

def verificar_token(credenciales: HTTPAuthorizationCredentials = Depends(security)):
    token = credenciales.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token inválido o expirado. Acceso denegado: {str(e)}")

# --- MODELOS DE DATOS ---
class ResultadoBatalla(BaseModel):
    juego: str
    fecha: str
    season: str
    jugador1: str
    jugador2: str
    faccion_j1: str
    faccion_j2: str
    resultado_j1: str
    rango_j1: str
    rango_j2: str
    puntos_j1: int
    puntos_j2: int

class NuevoOperativo(BaseModel):
    email: str
    rol: str

class NuevoEvento(BaseModel):
    juego: str
    titulo: str
    fecha: str
    link: str

# --- FUNCIONES DE BASE DE DATOS ---
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

# --- ENDPOINTS PÚBLICOS ---
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

@app.get("/api/facciones/{game_id}")
async def get_facciones(game_id: str):
    config = RANKINGS_CONFIG.get(game_id)
    if not config:
        return {"error": f"El ranking '{game_id}' no está configurado."}

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        if os.path.exists("credenciales.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.getenv("GOOGLE_SHEETS_CREDS")), scope)
            
        client = gspread.authorize(creds)
        spreadsheet = client.open(config["file"])
        
        sheet_graficas = spreadsheet.worksheet("Graficas")
        
        # Columna G es la número 7
        facciones_col = sheet_graficas.col_values(7)
        
        if len(facciones_col) > 1:
            facciones_limpias = sorted(list(set([
                str(f).strip() for f in facciones_col[1:] 
                if str(f).strip() and str(f).strip().lower() != "facciones"
            ])))
            return {"facciones": facciones_limpias}
            
        return {"facciones": []}

    except Exception as e:
        print(f"Error extrayendo facciones: {e}")
        return {"facciones": []}
    

@app.get("/api/jugadores/{game_id}")
async def get_jugadores(game_id: str):
    if game_id not in RANKINGS_CONFIG:
        return {"error": f"El ranking '{game_id}' no está configurado."}

    df = get_google_sheet_data(game_id)
    
    if df is None or df.empty:
        return {"jugadores": []}

    col_jugador = next((col for col in df.columns if "jugador" in col.lower() or "nombre" in col.lower() or "operativo" in col.lower()), None)
    
    if not col_jugador and len(df.columns) > 0:
        col_jugador = df.columns[0]
        
    if not col_jugador:
        return {"jugadores": []}

    jugadores_unicos = df[col_jugador].dropna().unique().tolist()
    jugadores_limpios = sorted(list(set([
        str(j).strip() for j in jugadores_unicos 
        if str(j).strip() and str(j).strip().lower() != "desconocido"
    ])))

    return {"jugadores": jugadores_limpios}
    

@app.get("/api/eventos/{game_id}")
async def obtener_eventos(game_id: str):
    try:
        db = firestore.client()
        eventos_ref = db.collection('eventos').where('juego', '==', game_id).stream()
        
        eventos = []
        for doc in eventos_ref:
            evento = doc.to_dict()
            evento['id'] = doc.id
            
            if 'creado_en' in evento:
                evento['creado_en'] = str(evento['creado_en'])
                
            eventos.append(evento)
            
        eventos_ordenados = sorted(eventos, key=lambda x: x.get('fecha', ''))
        
        return {"eventos": eventos_ordenados}

    except Exception as e:
        print(f"Error obteniendo cronograma: {e}")
        return {"eventos": []}


# --- ENDPOINTS PROTEGIDOS (Requieren Token de Firebase) ---

@app.post("/api/resultados")
async def registrar_resultado(datos: ResultadoBatalla, usuario_token=Depends(verificar_token)):
    config = RANKINGS_CONFIG.get(datos.juego)
    if not config:
        raise HTTPException(status_code=404, detail=f"El ranking '{datos.juego}' no está configurado.")

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        if os.path.exists("credenciales.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.getenv("GOOGLE_SHEETS_CREDS")), scope)

        client = gspread.authorize(creds)
        spreadsheet = client.open(config["file"])
        sheet = spreadsheet.worksheet("Logs")

        combate = f"{datos.jugador1} vs {datos.jugador2}"
        combate_faccion = f"{datos.faccion_j1} vs {datos.faccion_j2}"
        
        ganador, perdedor, faccion_ganadora, faccion_perdedora = "", "", "", ""
        empate_j1, empate_j2 = "NA", "NA"
        puntos_ganador, puntos_perdedor, puntos_empate_j1, puntos_empate_j2 = 0, 0, 0, 0

        if datos.resultado_j1 == "victoria":
            ganador, perdedor = datos.jugador1, datos.jugador2
            faccion_ganadora, faccion_perdedora = datos.faccion_j1, datos.faccion_j2
            puntos_ganador, puntos_perdedor = datos.puntos_j1, datos.puntos_j2
        elif datos.resultado_j1 == "derrota":
            ganador, perdedor = datos.jugador2, datos.jugador1
            faccion_ganadora, faccion_perdedora = datos.faccion_j2, datos.faccion_j1
            puntos_ganador, puntos_perdedor = datos.puntos_j2, datos.puntos_j1
        else: # empate
            empate_j1, empate_j2 = datos.jugador1, datos.jugador2
            puntos_empate_j1, puntos_empate_j2 = datos.puntos_j1, datos.puntos_j2

        nueva_fila = [
            datos.fecha, datos.season, combate, datos.jugador1, datos.jugador2,
            ganador, perdedor, datos.faccion_j1, datos.faccion_j2, datos.rango_j1,
            datos.rango_j2, combate_faccion, faccion_ganadora, faccion_perdedora,
            empate_j1, empate_j2, "Mismo Rango", puntos_ganador, puntos_perdedor,
            puntos_empate_j1, puntos_empate_j2
        ]

        sheet.append_row(nueva_fila)

        return {
            "mensaje": "Log de batalla registrado exitosamente",
            "operativo": usuario_token.get("email"),
            "datos": nueva_fila
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al escribir en los archivos: {str(e)}")

@app.post("/api/eventos")
async def registrar_evento(datos: NuevoEvento, usuario_token=Depends(verificar_token)):
    try:
        db = firestore.client()
        
        nuevo_evento = {
            "juego": datos.juego,
            "titulo": datos.titulo,
            "fecha": datos.fecha,
            "link": datos.link,
            "creado_por": usuario_token.get("email"),
            "creado_en": firestore.SERVER_TIMESTAMP
        }
        
        db.collection('eventos').add(nuevo_evento)

        return {
            "mensaje": "Misión agendada exitosamente en la base de datos central.", 
            "operativo": usuario_token.get("email")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo en la transmisión del evento: {str(e)}")

@app.put("/api/eventos/{evento_id}")
async def actualizar_evento(evento_id: str, datos: NuevoEvento, usuario_token=Depends(verificar_token)):
    try:
        db = firestore.client()
        evento_ref = db.collection('eventos').document(evento_id)
        
        evento_ref.update({
            "juego": datos.juego,
            "titulo": datos.titulo,
            "fecha": datos.fecha,
            "link": datos.link
        })

        return {"mensaje": "Misión actualizada exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al actualizar el evento: {str(e)}")

@app.delete("/api/eventos/{evento_id}")
async def eliminar_evento(evento_id: str, usuario_token=Depends(verificar_token)):
    try:
        db = firestore.client()
        db.collection('eventos').document(evento_id).delete()
        
        return {"mensaje": "Misión purgada de los registros."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al eliminar el evento: {str(e)}")

@app.post("/api/usuarios/rol")
async def asignar_rol(datos: NuevoOperativo, usuario_token=Depends(verificar_token)):
    try:
        db = firestore.client()
        admin_doc_ref = db.collection('roles').document(usuario_token['email'])
        admin_doc = admin_doc_ref.get()

        if not admin_doc.exists or admin_doc.to_dict().get('role') != 'superadmin':
            raise HTTPException(status_code=403, detail="Operación denegada. Solo un SuperAdmin puede asignar roles.")

        nuevo_usuario_ref = db.collection('roles').document(datos.email)
        nuevo_usuario_ref.set({'role': datos.rol})

        return {"mensaje": f"Permisos de '{datos.rol}' concedidos a {datos.email}."}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo en la asignación de credenciales: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
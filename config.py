"""
config.py — Configuración de conexión a MySQL (y SMTP si aplica).

Responsable: Persona 1 (base de datos / servidor).

Qué debe hacer este archivo:
1. Definir las credenciales de conexión a MySQL como constantes o desde
   variables de entorno (recomendado: usar .env + python-dotenv para no
   subir contraseñas al repositorio).
2. Definir aquí también, si aplica, los datos de SMTP para reportes.py.

Esqueleto:
"""

import os

DB_CONFIG = {
   "host": "localhost",
   "port": 3306,
   "user": "root",
   "password": "sigito2026",
   "database": "sigito_db",

}

SQLITE_LOCAL_PATH = "sigito_local.db"

# --- SMTP (reportes / notificaciones) ---
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = os.getenv("SIGITO_SMTP_USER", "")
SMTP_APP_PASSWORD = os.getenv("SIGITO_SMTP_APP_PASSWORD", "")  # TODO: cifrar si se guarda en BD

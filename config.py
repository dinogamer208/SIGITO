"""
config.py — Configuración de conexión a MySQL (y SMTP si aplica).

Responsable: Persona 1 (base de datos / servidor).

Los valores de abajo son el default para desarrollo local (cada quien
con su propio MySQL en su PC, usuario root / password sigito2026).

Cuando exista un servidor central, cada PC solo necesita un archivo
`.env` (no se sube al repo, ver .gitignore) con, por ejemplo:

    SIGITO_DB_HOST=192.168.1.50
    SIGITO_DB_PORT=3306
    SIGITO_DB_USER=sigito_app
    SIGITO_DB_PASSWORD=la-password-real
    SIGITO_DB_NAME=sigito_db

No hace falta tocar este archivo ni el código para hacer el cambio.
"""

import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
   "host": os.getenv("SIGITO_DB_HOST", "localhost"),
   "port": int(os.getenv("SIGITO_DB_PORT", "3306")),
   "user": os.getenv("SIGITO_DB_USER", "root"),
   "password": os.getenv("SIGITO_DB_PASSWORD", "300109"),
   "database": os.getenv("SIGITO_DB_NAME", "sigito_db"),
   "charset": "utf8mb4",
   "collation": "utf8mb4_unicode_ci"

}

SQLITE_LOCAL_PATH = "sigito_local.db"

# --- SMTP (reportes / notificaciones) ---
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = os.getenv("SIGITO_SMTP_USER", "")
SMTP_APP_PASSWORD = os.getenv("SIGITO_SMTP_APP_PASSWORD", "")  # TODO: cifrar si se guarda en BD

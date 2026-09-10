"""
config.py — Configuración de conexión a MySQL (y SMTP si aplica).

Responsable: Persona 1 (base de datos / servidor).

Ningún valor sensible (host/usuario/contraseña reales) vive en este
archivo: se leen de un `.env` en la raíz del proyecto, que NO se sube
al repo (ver .gitignore). Copia `.env.example` a `.env` y rellena tus
valores locales:

    cp .env.example .env

    SIGITO_DB_HOST=localhost
    SIGITO_DB_PORT=3306
    SIGITO_DB_USER=root
    SIGITO_DB_PASSWORD=tu-password-local
    SIGITO_DB_NAME=sigito_db

Los defaults de abajo solo cubren host/puerto/usuario/nombre para no
tener que escribir todo; la contraseña siempre viene del `.env`.
"""

import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
   "host": os.getenv("SIGITO_DB_HOST", "localhost"),
   "port": int(os.getenv("SIGITO_DB_PORT", "3306")),
   "user": os.getenv("SIGITO_DB_USER", "root"),
   "password": os.getenv("SIGITO_DB_PASSWORD", ""),
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

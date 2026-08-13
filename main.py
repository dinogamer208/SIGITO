"""
main.py — Punto de entrada de SIGITO.

Flujo: verifica conexión a MySQL -> LoginView -> (login exitoso) -> Dashboard.
Al cerrar sesión desde el Dashboard, vuelve a mostrar LoginView.
"""

import threading

import tkinter as tk
from tkinter import messagebox

from views.tema import aplicar_tema
from db.conexion import hay_conexion_servidor, obtener_conexion


def _precalentar_pool():
    """
    Abre y libera una conexión para forzar la creación del pool de
    conexiones (db/conexion.py) en un hilo aparte, mientras el usuario
    todavía está mirando/llenando el login. Así el costo de abrir las
    conexiones del pool no se siente como demora al iniciar sesión.
    """
    try:
        obtener_conexion().close()
    except Exception:
        pass  # si falla, cada consulta seguirá intentando conectar normalmente


def _mostrar_error_conexion():
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Error de conexión",
        "No se pudo conectar al servidor de MySQL.\n\n"
        "Verifica que el servicio esté corriendo y que config.py "
        "tenga los datos correctos (host, puerto, usuario, contraseña)."
    )
    root.destroy()


def mostrar_login():
    from views.login_view import LoginView
    LoginView(on_login_exitoso=mostrar_dashboard).mainloop()


def mostrar_dashboard(usuario):
    from dashboard_view import Dashboard
    Dashboard(usuario=usuario, on_logout=mostrar_login).mainloop()


def main():
    aplicar_tema()

    if not hay_conexion_servidor():
        _mostrar_error_conexion()
        return

    threading.Thread(target=_precalentar_pool, daemon=True).start()

    try:
        mostrar_login()
    except Exception as error:
        _root = tk.Tk()
        _root.withdraw()
        messagebox.showerror("Error inesperado", str(error))
        _root.destroy()
        raise


if __name__ == "__main__":
    main()

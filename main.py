"""
main.py — Punto de entrada de SIGITO.

Responsable: se arma en conjunto una vez cada módulo esté listo.

Qué debe hacer este archivo:
1. Importar la config y verificar conexión a la base de datos (db/conexion.py).
2. Levantar la ventana principal de Tkinter.
3. Mostrar primero login_view; si el login es exitoso, abrir main_menu_view.
4. Centralizar el manejo de errores no capturados (try/except alrededor del mainloop).

Esqueleto:
"""

import tkinter as tk
# from db.conexion import obtener_conexion
# from views.login_view import LoginView


def main():
    root = tk.Tk()
    root.title("SIGITO - Sistema de Gestión de Inventario Tecnológico/Ofimático")
    root.geometry("900x600")

    # TODO: probar conexión a la base de datos aquí antes de mostrar la UI
    # TODO: instanciar LoginView(root) y arrancar el flujo de login -> menú

    root.mainloop()


if __name__ == "__main__":
    main()

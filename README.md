# SIGITO - Sistema de Gestión de Inventario Tecnológico/Ofimático

Sistema para el control de inventario de equipo tecnológico y ofimático
de la institución: altas, bajas, préstamos, devoluciones y reportes.
Desarrollado por un equipo de 6 personas, en la misma línea de trabajo
que Café Nova (Python + Tkinter + MySQL), pero desde el inicio con
servidor en red, modo offline y escáneres de código de barras.

## Estructura de carpetas

```
SIGITO/
│
├── main.py                        # Punto de entrada, arranca la app
├── config.py                      # PLANTILLA de conexión (sin credenciales reales)
├── requirements.txt                 # Dependencias del proyecto
├── .gitignore                       # Archivos que NO se suben al repo
│
├── db/
│   ├── conexion.py                 # (Persona 1) Conexión MySQL + modo offline/sincronización
│   ├── schema.sql                  # (Persona 1) Script CREATE TABLE completo
│   └── seed_data.sql               # (Persona 1 + datos de Persona 6) Datos de prueba
│
├── models/
│   ├── usuario.py                  # (Persona 2) Usuario y ProfesorAutorizado
│   ├── articulo.py                 # (Persona 1) Articulo
│   ├── asignacion.py               # (Persona 3) Asignacion
│   └── mantenimiento.py            # (Persona 4) Mantenimiento
│
├── controllers/
│   ├── auth_controller.py          # (Persona 2) Login, profesores autorizados
│   ├── inventario_controller.py    # (Persona 1) CRUD artículos, códigos de barras ✅ TERMINADO
│   ├── asignacion_controller.py    # (Persona 3) Préstamos y devoluciones
│   └── reportes_controller.py      # (Persona 4) Monitor de correos + reportes
│
├── views/
│   ├── login_view.py                # (Persona 5) Pantalla de login
│   ├── main_menu_view.py            # (Persona 5) Menú principal
│   ├── inventario_view.py           # (Persona 1 + 5) Pantalla de inventario
│   ├── asignacion_view.py           # (Persona 3 + 5) Pantalla de asignaciones
│   └── reportes_view.py             # (Persona 4 + 5) Pantalla de reportes
│
├── utils/
│   ├── validaciones.py              # Validación de formularios (compartido)
│   ├── seguridad.py                 # Hash de contraseñas, Fernet
│   └── exportador.py                # (Persona 4) Estilo reutilizable para Excel
│
├── assets/                          # (Persona 5) Logo, íconos, etiquetas, fotos
│   └── etiquetas/                   # Generadas por Persona 1, NO se suben al repo
│
└── docs/                            # (Persona 6) Manual, checklist, presentación
```

## Reparto de personas

| Persona | Responsabilidad principal | Estado |
|---|---|---|
| **1** | BD + Servidor + Inventario + Códigos de barras | Módulo de lógica terminado y probado |
| **2** | Usuarios (login) y profesores autorizados | Sin empezar |
| **3** | Asignaciones (préstamos y devoluciones) | Sin empezar |
| **4** | Correos, notificaciones y reportes | Sin empezar |
| **5** | Diseño de interfaz (todas las pantallas) | Sin empezar |
| **6** | Documentación, pruebas manuales y datos de ejemplo | Sin empezar |

## Cómo empezar (para cada integrante del equipo)

### 1. Clonar el repositorio
```bash
git clone https://github.com/TU_USUARIO/SIGITO.git
cd SIGITO
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Instalar MySQL Server en tu propia PC (para desarrollo local)
No necesitas el servidor real de la institución para programar tu módulo.
Instala MySQL Community Server (Developer Default) en tu computadora:
https://dev.mysql.com/downloads/installer/

### 4. Ejecutar el esquema de la base de datos
Abre la terminal de MySQL Command Line (o Workbench) y corre:
```sql
source RUTA\SIGITO\db\schema.sql
```
Esto crea la base `sigito_db` y todas las tablas.

### 5. Crear tu configuración local (IMPORTANTE)
El archivo `config.py` del repositorio es solo una plantilla sin
contraseña real. Cada persona debe:

1. Copiar `config.py` como `config_local.py` (ya está en `.gitignore`,
   nunca se sube al repo).
2. Poner ahí su propia contraseña de MySQL local.
3. Cambiar el import en los archivos que uses, de:
   ```python
   from config import DB_CONFIG
   ```
   a:
   ```python
   from config_local import DB_CONFIG
   ```
   (Cuando el servidor real esté listo, `config_local.py` solo cambia
   el host de "localhost" a la IP del servidor, ej. 192.168.10.10).

### 6. Trabajar en tu propia rama, nunca directo en main
```bash
git checkout -b feature/nombre-de-tu-modulo
```
Ejemplos: feature/asignaciones, feature/diseño-interfaz,
feature/reportes-correos, feature/usuarios.

Cuando termines tu parte:
```bash
git add .
git commit -m "Descripción clara de lo que hiciste"
git push origin feature/nombre-de-tu-modulo
```
Y abre un Pull Request en GitHub hacia main para que el equipo lo
revise antes de integrarlo.

## Decisiones ya acordadas por el equipo (reflejadas en el código guía)

- Sin límite de préstamos simultáneos por estudiante.
- Un artículo solo se puede prestar si está "disponible"; cualquier
  usuario con sesión activa puede registrar la devolución.
- Profesores autorizados: solo catálogo (sin login propio), editable
  por completo (nombre, correo, teléfono) desde Gestión de Usuarios.
- Ante un atraso: se envían DOS correos (alumno + profesor) y una
  notificación nativa de Windows. El monitor corre cada 5 minutos y
  SIEMPRE contra el servidor central (nunca offline).
- Servidor Ubuntu Server LTS con dos adaptadores: LAN interna (MySQL)
  y WiFi (solo para envío de correos SMTP).
- Modo offline con SQLite local: permitido para consultas y
  devoluciones; NO permitido para crear artículos nuevos; las
  asignaciones nuevas offline se marcan "pendiente de confirmar".
- 2 escáneres de código de barras USB (modo HID/teclado), uno en
  Inventario y otro en Asignaciones — no requieren drivers.
- Las etiquetas de código de barras incluyen el nombre del artículo
  arriba del código, generadas con python-barcode + Pillow.

## Módulo de Inventario (Persona 1) — ya funcional, referencia para los demás

Estas funciones ya están probadas contra MySQL real y pueden usarse
como ejemplo de cómo estructurar los demás controllers:

- generar_codigo_inventario(prefijo) — genera TEC-0001, OFI-0001, etc.
- agregar_articulo(datos)
- editar_articulo(id, datos)
- dar_de_baja(id)
- listar_articulos(categoria_id=None, estado_disponibilidad=None)
- buscar_articulo_por_codigo(codigo) — usada por el escáner
- generar_etiqueta(codigo_inventario, nombre_articulo) — genera el PNG
  de la etiqueta en assets/etiquetas/

El archivo probar_inventario.py en la raíz (no se sube al repo) sirve
como banco de pruebas de consola antes de conectar la lógica a la
interfaz gráfica — se recomienda que cada persona haga lo mismo con su
propio módulo (probar_asignaciones.py, probar_auth.py, etc.).

## Orden recomendado de trabajo

1. Persona 1 entrega db/schema.sql + db/conexion.py funcional -- LISTO
2. Persona 5 entrega wireframes/estilo base antes de programar las vistas
3. Personas 2 y 3 avanzan en paralelo (ya pueden empezar)
4. Persona 4 depende de que existan las tablas de Persona 2 y 3
5. Persona 6 documenta desde el inicio y hace pruebas al final

## Notas importantes

- Cada archivo .py y db/schema.sql tienen, en su comentario inicial,
  instrucciones de qué debe implementarse ahí y un ejemplo de armazón.
- db/schema.sql ya no tiene TODOs pendientes: está completo y probado
  por Persona 1.
- El archivo config.py en el repo NUNCA debe tener contraseñas reales.
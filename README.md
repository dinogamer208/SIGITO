# SIGITO — Sistema de Gestión de Inventario Tecnológico/Ofimático

Sistema de escritorio (Python + CustomTkinter + MySQL, 100% local, sin
servidor en red) para el control de inventario de equipo tecnológico y
ofimático de una institución: altas, bajas, préstamos, devoluciones,
mantenimientos, reportes, auditoría y administración de usuarios con
roles.

Existe en dos versiones idénticas en funcionalidad:

- **`SIGITO/`** — el proyecto fuente (Python), para desarrollo.
- **`SIGITO App/`** — la versión empaquetada como `SIGITO.exe`
  (PyInstaller) + MySQL portable, para instalar en una PC sin Python.
  Se reconstruye desde el código fuente con `python -m PyInstaller
  SIGITO.spec` cada vez que el código fuente cambia.

## Funcionalidades

### Inventario
- Alta, edición, baja y **reactivar** (revertir una baja hecha por
  error) de artículos, con categorías propias.
- **Eliminar** un artículo por completo (distinto de "dar de baja"):
  solo funciona si nunca tuvo historial/préstamos; si ya tiene
  actividad, el sistema pide desactivarlo en su lugar.
- Cada artículo es un *tipo* con `cantidad_total`/`cantidad_disponible`
  (no una fila por unidad física).
- Fotos de artículos (selección de archivo o cámara), código de barras
  generado o escaneado (lector USB tipo teclado), etiquetas imprimibles
  con el nombre del artículo.
- **Paginación de 10 en 10** (con "Anterior"/"Siguiente") en vez de
  cargar todo el listado de un jalón.
- **Filtros** por categoría y por estado (Disponible/Agotado/De baja),
  combinables con la búsqueda por texto/escaneo.

### Asignaciones (préstamos y devoluciones)
- Registro de préstamo con escaneo de código de barras, foto del
  alumno (cámara), profesor autorizante, cantidad, fecha/hora de
  devolución esperada.
- Registro de devolución, historial de devoluciones recientes.
- **Enviar a mantenimiento** (solo admin): saca una unidad de
  circulación con destino, causa, técnico, costo estimado, fecha de
  envío y fecha estipulada de devolución (con escaneo de código de
  barras para elegir el equipo); tarjeta de "Equipos en mantenimiento"
  con botón para marcarlos como regresados (restaura el stock).

### Reportes
- Resumen de inventario por estado, préstamos vencidos, artículos por
  categoría, asignaciones por mes, artículos más prestados.
- Exportar a CSV/Excel/PDF (solo admin). Un usuario **limitado** no
  exporta nada: solo tiene el botón **"Ver PDF"**, que abre el reporte
  para consulta sin pasar por un diálogo de "guardar como".

### Historial de auditoría
- Pantalla propia (`views/historial_view.py`, solo admin) con todos los
  movimientos del sistema (alta, préstamo, devolución, baja,
  mantenimiento), filtrable por tipo y por texto libre, paginado de 10
  en 10, exportable a CSV/Excel.

### Roles y usuarios
Dos roles (`usuarios.rol`): **admin** (acceso total) y **limitado**.
Un usuario limitado:
- Solo ve, en el sidebar: Dashboard, Inventario, Asignaciones,
  Reportes, Configuración (sin Historial ni Usuarios).
- En Inventario, solo las acciones "Barras" y "Baja"/"Reactivar" (sin
  Editar, Eliminar, Nuevo artículo ni Categorías).
- En Reportes, solo "Ver PDF" (sin exportar).
- En Configuración, solo la pestaña de Contraseña — y para cambiarla
  necesita la contraseña de un **admin** como autorización (en vez de
  su propia contraseña actual).

Desde **Configuración → Usuarios** (solo admin) se puede: agregar
usuarios (nombre, usuario, contraseña, rol), restablecer la contraseña
de cualquiera, activar/desactivar, y eliminar (solo si el usuario nunca
tuvo actividad registrada). Nunca se puede desactivar/eliminar al
único admin activo que quede.

### Recuperación de cuenta (sin tocar la base de datos a mano)
Desde el login, **"¿Olvidaste tu contraseña?"** ofrece dos métodos:
1. **Código de recuperación** — un código permanente que el admin
   genera y ve una sola vez desde Configuración → Recuperación; de un
   solo uso (se invalida al usarlo, hay que generar uno nuevo).
2. **Código por correo** — un código temporal de 6 dígitos (30 min),
   enviado al correo de recuperación que el usuario haya registrado,
   usando el SMTP ya configurado.

Si ninguno de los dos aplica a esa cuenta (típicamente un usuario
limitado, que no genera su propio código), se muestra el **contacto de
soporte** (teléfono, coordinador, correo) configurado en Configuración
→ Recuperación.

**Límite de intentos:** máximo 5 intentos fallidos (compartido entre
ambos métodos); al 5º, bloquea la recuperación de esa cuenta por 15
minutos (no permanente, para no dejar a un admin sin ninguna forma de
entrar). Se resetea al generar un código nuevo o al recuperar con
éxito.

### Monitor de correos y notificaciones (automático, cada 5 min)
`utils/monitor.py` corre en un hilo en segundo plano mientras hay
sesión activa: revisa préstamos vencidos, envía el correo de aviso
(alumno, vía SMTP) y **siempre** dispara una notificación nativa de
Windows (`winotify`) — incluso si el SMTP no está configurado. Usa
`asignaciones.correo_aviso_enviado` para no avisar dos veces del mismo
préstamo.

### Respaldo automático del inventario
`utils/respaldo.py`: si se activa desde Configuración → Base de datos,
genera cada N horas un `.zip` del inventario **con fotos** en
`backups/`, y borra los respaldos más viejos (conserva los últimos 10).

### Exportar / cargar inventario
Configuración → Base de datos:
- **Descargar CSV / Excel** — todo el inventario actual.
- **Descargar con fotos (.zip)** — igual, pero empaqueta también una
  copia de cada foto de artículo.
- **Cargar inventario...** — acepta CSV, Excel o el `.zip` con fotos:
  crea artículos nuevos o actualiza los existentes (comparando por
  código de inventario), crea categorías que falten, y si es un `.zip`
  restaura también las fotos. Pensado para pasar el inventario de una
  instalación de SIGITO a otra (ej. de `SIGITO/` a `SIGITO App/`).

### Zona de peligro
Configuración → Base de datos → **Borrar base de datos**: pide la
contraseña de la sesión activa + una doble confirmación, y borra todo
el inventario, préstamos, historial, mantenimientos, profesores y
configuración de correo — **sin tocar la tabla de usuarios**, para
seguir pudiendo iniciar sesión después.

### Otros detalles de UI
- Botón "Ver" (mostrar/ocultar) en **todos** los campos de contraseña
  de la aplicación (`views/componentes.py:crear_campo_password`).
- Modo claro/oscuro (toggle en el sidebar).
- Configuración organizada en **pestañas** (CTkTabview): Contraseña,
  Correo, Usuarios, Base de datos, Recuperación, Diagnóstico. Un
  usuario limitado ve solo la tarjeta de Contraseña, sin pestañas.

## Estructura de carpetas

```
SIGITO/
├── main.py                          # Punto de entrada; arranca monitor + respaldo al hacer login
├── dashboard_view.py                # Pantalla principal tras login (sidebar según rol)
├── config.py                        # Lee la conexión del .env (sin credenciales en el código)
├── .env.example                     # Plantilla: cp .env.example .env
├── requirements.txt
├── SIGITO.spec                      # Config de PyInstaller para generar el .exe
├── seed_admin.py / crear_usuario_admin.py   # Crear/resetear el usuario admin inicial
│
├── db/
│   ├── conexion.py                  # Pool de conexiones MySQL
│   ├── schema.sql                   # Esquema completo (para una instalación nueva)
│   └── migraciones/                 # 000 a 007, aplicar en orden en una BD ya existente
│
├── models/                          # Articulo, Asignacion, Usuario, Mantenimiento
│
├── controllers/
│   ├── auth_controller.py           # Login, roles, usuarios, recuperación de cuenta, profesores
│   ├── inventario_controller.py     # CRUD artículos/categorías, import/export, códigos de barras
│   ├── asignacion_controller.py     # Préstamos y devoluciones
│   ├── mantenimiento_controller.py  # Enviar a mantenimiento / marcar regresado
│   ├── config_controller.py         # configuracion (correo, respaldo, soporte), correos SMTP
│   └── reportes_controller.py       # Consultas para Reportes
│
├── views/
│   ├── login_view.py                # Login + modal de recuperación de cuenta
│   ├── dashboard_view.py            # (junto a la raíz) sidebar filtrado por rol
│   ├── inventario_view.py           # Paginación, filtros, fotos, acciones por rol
│   ├── asignacion_view.py           # Préstamos/devoluciones + envío a mantenimiento
│   ├── reportes_view.py             # Exportar (admin) / Ver PDF (limitado)
│   ├── historial_view.py            # Auditoría completa (solo admin)
│   ├── usuarios_view.py             # Profesores autorizados (catálogo, no login)
│   ├── config_view.py               # Configuración por pestañas
│   ├── componentes.py               # Widgets compartidos (cards, badges, tabla, campo password)
│   └── tema.py                      # Paleta de colores claro/oscuro
│
├── utils/
│   ├── seguridad.py                 # bcrypt (contraseñas) + Fernet (SMTP cifrado)
│   ├── auditoria.py                 # historial_movimientos (registrar / listar)
│   ├── exportador.py                # CSV / Excel / PDF / ZIP con fotos
│   ├── monitor.py                   # Hilo: correos + notificaciones de atraso cada 5 min
│   ├── respaldo.py                  # Hilo: respaldo automático periódico del inventario
│   ├── notificaciones.py            # Envoltorio de winotify (toast nativo de Windows)
│   ├── diagnostico.py               # Chequeos de Configuración → Diagnóstico
│   └── validaciones.py
│
├── assets/                          # Fotos de artículos/préstamos, etiquetas de código de barras
├── tests/                           # pytest (utils/seguridad, validaciones)
└── docs/
```

## Roles y permisos (resumen)

| Área | Admin | Limitado |
|---|---|---|
| Dashboard, Inventario (ver), Asignaciones, Reportes (ver) | ✅ | ✅ |
| Inventario: Editar / Eliminar / Nuevo artículo / Categorías | ✅ | ❌ |
| Inventario: Barras / Baja / Reactivar | ✅ | ✅ |
| Asignaciones: Nuevo préstamo / Devolver | ✅ | ✅ |
| Asignaciones: Enviar a mantenimiento | ✅ | ❌ |
| Reportes: Exportar CSV/Excel/PDF | ✅ | ❌ (solo "Ver PDF") |
| Historial de auditoría | ✅ | ❌ (oculto) |
| Usuarios (profesores autorizados) | ✅ | ❌ (oculto) |
| Configuración: Contraseña | ✅ (propia) | ✅ (con autorización de admin) |
| Configuración: Correo/Usuarios/BD/Recuperación/Diagnóstico | ✅ | ❌ |

## Migraciones de base de datos

Si ya tienes una base de datos de SIGITO creada con un `schema.sql`
anterior, aplica en orden las que falten (revisa qué hay en
`control_versiones`):

| Migración | Qué agrega |
|---|---|
| 001_esquema_inicial | Esquema base |
| 002_configuracion | Tabla `configuracion` (correo SMTP) |
| 003_foto_prestamo | `asignaciones.foto_alumno` |
| 004_stock | `cantidad_total`/`cantidad_disponible`, quita `'prestado'` de `estado_disponibilidad` |
| 005_roles_y_mantenimiento | Rol `'limitado'`; `mantenimientos.destino/fecha_retorno_estimada/estado` |
| 006_recuperacion_cuenta | `usuarios.correo`, `recovery_code_hash`, `recovery_email_code_hash/expira` |
| 007_limite_intentos_recuperacion | `usuarios.recovery_intentos_fallidos`, `recovery_bloqueado_hasta` |

Una base de datos creada desde el `schema.sql` actual ya incluye todo
lo anterior — las migraciones solo son necesarias para una BD que ya
existía antes de cada cambio.

## Cómo empezar (desarrollo)

### 1. Clonar / abrir el proyecto
```bash
cd SIGITO
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```
Incluye `winotify` (notificaciones nativas de Windows — requiere
Windows 10/11).

### 3. MySQL local
Instala MySQL Community Server y corre `db/schema.sql` (crea
`sigito_db` con todo, usuario admin incluido: `admin` / `admin123` —
cámbiala en el primer inicio de sesión, o desde Configuración).

### 4. Configurar `.env`
```bash
cp .env.example .env
```
Rellena `SIGITO_DB_PASSWORD` (y el resto si tu MySQL no usa los
defaults). `config.py` nunca lleva credenciales reales — todo sale del
`.env`, que está en `.gitignore`.

### 5. Correr la app
```bash
python main.py
```

### 6. Generar el `.exe` (SIGITO App)
```bash
python -m PyInstaller SIGITO.spec --noconfirm
```
El resultado queda en `dist/SIGITO.exe`; cópialo a `SIGITO App/SIGITO.exe`
para actualizar la versión empaquetada.

## Notas de seguridad

- Contraseñas de login: bcrypt (`utils/seguridad.py`, costo 10).
- Contraseña de aplicación SMTP: cifrada con Fernet; la llave vive
  fuera del repo, en `~/.sigito/secret.key` (se genera sola la primera
  vez — si mueves el proyecto a otra PC y quieres conservar los
  valores cifrados, copia también ese archivo).
- Código de recuperación y código por correo: se guardan **hasheados**
  (nunca en texto plano), de un solo uso, con límite de 5 intentos y
  bloqueo temporal de 15 minutos.
- `config.py` en el repo nunca debe tener contraseñas reales.

## Pruebas

```bash
pytest
```
Cubre `utils/seguridad.py` y `utils/validaciones.py` (ver `tests/README.md`).

## Historial del proyecto

SIGITO arrancó como trabajo en equipo (6 personas, cada quien un
módulo: BD/Inventario, Usuarios, Asignaciones, Correos/Reportes,
Diseño de interfaz, Documentación/QA) en la misma línea que Café Nova
(Python + Tkinter + MySQL). Desde esa base se agregaron, en pasadas
posteriores: paginación y filtros de inventario, eliminar/reactivar
artículos, exportar/cargar el inventario (con fotos), respaldo
automático, monitor de correos + notificaciones nativas, historial de
auditoría, roles de usuario con permisos granulares, gestión de
usuarios (crear/restablecer/desactivar/eliminar), el módulo de
mantenimiento, recuperación de cuenta (código local + correo) con
límite de intentos, y la reorganización de Configuración en pestañas.

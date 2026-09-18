# instalar.ps1 - Provisiona el MySQL local que SIGITO necesita en una PC nueva.
# Ejecutar UNA SOLA VEZ en cada PC (via instalar.bat, que pide permisos de
# administrador), antes de abrir SIGITO.exe por primera vez.
#
# Qué hace:
#   1. Si ya hay un MySQL escuchando en el host/puerto del .env, no toca nada.
#   2. Si no, usa el MySQL Server portátil incluido en la carpeta
#      "mysql-portable" (junto a este script) -- no necesita internet ni
#      instalador gráfico. Si esa carpeta no está, intenta descargarlo.
#      Copia lo necesario a %LOCALAPPDATA%\SIGITO\mysql, lo registra como
#      servicio de Windows ("SIGITO_MySQL") y le pone la contraseña de
#      root del .env.
#   3. Crea la base `sigito_db` con todas las tablas (db\schema.sql) y un
#      usuario admin por defecto (admin / admin123).

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile    = Join-Path $ScriptDir ".env"
$SchemaFile = Join-Path $ScriptDir "db\schema.sql"

if (-not (Test-Path $EnvFile)) {
    Write-Host "No se encontró .env junto a este script ($EnvFile)." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $SchemaFile)) {
    Write-Host "No se encontró db\schema.sql junto a este script ($SchemaFile)." -ForegroundColor Red
    exit 1
}

$envVars = @{}
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        $envVars[$matches[1]] = $matches[2].Trim()
    }
}

$DbHost = $envVars['SIGITO_DB_HOST']
if (-not $DbHost) { $DbHost = 'localhost' }
$Port = 3306
if ($envVars['SIGITO_DB_PORT']) { $Port = [int]$envVars['SIGITO_DB_PORT'] }
$RootPass = $envVars['SIGITO_DB_PASSWORD']
$DbName = $envVars['SIGITO_DB_NAME']
if (-not $DbName) { $DbName = 'sigito_db' }

$ConnectHost = $DbHost
if ($ConnectHost -eq 'localhost') { $ConnectHost = '127.0.0.1' }

$InstallDir  = "$env:LOCALAPPDATA\SIGITO\mysql"
$DataDir     = "$InstallDir\data"
$IniFile     = "$InstallDir\my.ini"
$ServiceName = "SIGITO_MySQL"
$BundledDir  = Join-Path $ScriptDir "mysql-portable"
$ZipUrl      = "https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.46-winx64.zip"
$MysqlExe    = "$InstallDir\bin\mysql.exe"
$MysqldExe   = "$InstallDir\bin\mysqld.exe"

function Test-Puerto($h, $p) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($h, $p, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(1500)
        if ($ok -and $client.Connected) { $client.Close(); return $true }
        $client.Close()
        return $false
    } catch { return $false }
}

function Salir-ConError($mensaje) {
    Write-Host $mensaje -ForegroundColor Red
    exit 1
}

Write-Host "== Instalador de base de datos SIGITO ==" -ForegroundColor Cyan

if ($DbHost -ne 'localhost' -and $DbHost -ne '127.0.0.1') {
    Write-Host "El .env apunta a un servidor remoto ($DbHost)." -ForegroundColor Yellow
    Write-Host "Este instalador solo provisiona MySQL local; si esta PC debe" -ForegroundColor Yellow
    Write-Host "conectarse al servidor central, solo necesitas red hacia $DbHost, no instalar nada aqui." -ForegroundColor Yellow
    exit 0
}

if (Test-Puerto $ConnectHost $Port) {
    Write-Host "Ya hay un servidor MySQL escuchando en ${ConnectHost}:${Port}. Se usará ese." -ForegroundColor Green
} else {
    if (-not (Test-Path $MysqldExe)) {
        if (Test-Path "$BundledDir\bin\mysqld.exe") {
            Write-Host "Copiando el MySQL portátil incluido..."
            New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
            Copy-Item "$BundledDir\*" $InstallDir -Recurse -Force
            Write-Host "MySQL listo en $InstallDir" -ForegroundColor Green
        } else {
            Write-Host "No se encontró MySQL en esta PC ni la carpeta 'mysql-portable'. Descargando MySQL Server 8.0 (~200 MB, puede tardar varios minutos)..."
            New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
            $zipPath = "$env:TEMP\sigito_mysql.zip"
            Invoke-WebRequest -Uri $ZipUrl -OutFile $zipPath
            $extractDir = "$env:TEMP\sigito_mysql_extract"
            if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
            Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
            $inner = Get-ChildItem $extractDir -Directory | Select-Object -First 1
            Copy-Item "$($inner.FullName)\*" $InstallDir -Recurse -Force
            Remove-Item $zipPath -Force
            Remove-Item $extractDir -Recurse -Force
            Write-Host "MySQL descargado en $InstallDir" -ForegroundColor Green
        }
    }

    if (-not (Test-Path $IniFile)) {
        Write-Host "Escribiendo configuración ($IniFile)..."
        @"
[mysqld]
datadir=$DataDir
basedir=$InstallDir
port=$Port
bind-address=127.0.0.1
"@ | Set-Content -Path $IniFile -Encoding ascii
    }

    if (-not (Test-Path "$DataDir\mysql")) {
        Write-Host "Inicializando la base de datos (primera vez)..."
        New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
        & $MysqldExe --initialize-insecure --datadir="$DataDir" --basedir="$InstallDir"
        if ($LASTEXITCODE -ne 0) { Salir-ConError "No se pudo inicializar la base de datos (mysqld --initialize-insecure falló)." }
    }

    if (-not (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)) {
        Write-Host "Registrando el servicio de Windows '$ServiceName'..."
        & $MysqldExe --install $ServiceName --defaults-file="$IniFile"
        if ($LASTEXITCODE -ne 0) { Salir-ConError "No se pudo registrar el servicio '$ServiceName'. ¿Estás ejecutando esto como Administrador?" }
    }

    Write-Host "Iniciando el servicio (arranque automático en cada reinicio)..."
    Set-Service -Name $ServiceName -StartupType Automatic
    Start-Service $ServiceName

    $listo = $false
    for ($i = 0; $i -lt 20; $i++) {
        if (Test-Puerto '127.0.0.1' $Port) { $listo = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $listo) { Salir-ConError "El servicio '$ServiceName' no respondió en el puerto $Port a tiempo." }

    Write-Host "Configurando la contraseña de 'root'..."
    & $MysqlExe -h "127.0.0.1" -P "$Port" -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$RootPass'; FLUSH PRIVILEGES;"
    if ($LASTEXITCODE -ne 0) { Salir-ConError "No se pudo configurar la contraseña de root." }
}

Write-Host "Creando la base de datos '$DbName' y sus tablas (si no existen)..."
$createOnly = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DbName' AND table_name='usuarios';"
$existe = & $MysqlExe -h "$ConnectHost" -P "$Port" -u root -p"$RootPass" -N -s -e $createOnly
if ($existe -match '1') {
    Write-Host "La base de datos ya tenía tablas; no se vuelve a correr schema.sql (para no borrar datos)." -ForegroundColor Yellow
} else {
    Get-Content $SchemaFile -Raw | & $MysqlExe -h "$ConnectHost" -P "$Port" -u root -p"$RootPass"
    if ($LASTEXITCODE -ne 0) { Salir-ConError "Falló al crear la base de datos desde schema.sql." }
    Write-Host "Base de datos creada." -ForegroundColor Green
}

Write-Host ""
Write-Host "Listo. Ya puedes abrir SIGITO.exe." -ForegroundColor Green
Write-Host "Usuario: admin   Contraseña: admin123 (cámbiala luego desde Configuración)." -ForegroundColor Green

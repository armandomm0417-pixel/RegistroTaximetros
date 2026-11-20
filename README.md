# Registro de Taxímetros Vendidos

Aplicación de escritorio para Windows que registra las ventas de taxímetros. Guarda los datos localmente en SQLite e incluye un sistema de actualizaciones automáticas desde **GitHub Releases**.

## Campos que registra

- Nombre del cliente
- Número de serie del taxímetro (único: evita duplicados)
- Tipo de carro (SEDÁN, SUV, Hatchback, Pickup, Camioneta, Van, Mototaxi u Otro)
- Placas
- Teléfono
- Fecha de venta (se rellena con la fecha actual)

## Funciones

- Interfaz moderna con panel lateral, tarjetas de indicadores y tabla de historial
- Alta, edición y eliminación de registros
- Búsqueda por cualquier campo (cliente, serie, placas, teléfono, fecha, etc.)
- Exportación a CSV compatible con Excel
- Actualización automática desde GitHub Releases con verificación SHA256
- Funciona sin conexión: internet solo se usa para buscar actualizaciones

## 1. Ejecutar desde el código fuente

Necesitas Python 3.10 o superior. La aplicación usa solo librerías incluidas en Python, así que no hay que instalar dependencias para ejecutarla.

```bat
cd RegistroVentas
python main.py
```

## 2. Generar el ejecutable .exe

```bat
pip install -r requirements.txt
build.bat
```

El ejecutable se crea en `dist\RegistroTaximetros.exe`. Cópialo, junto con el archivo de configuración de actualizaciones (paso 3), en la carpeta donde quieras instalar el programa, por ejemplo `C:\Taximetros\`.

Para cambiar la versión en una compilación local, edita `version.json`:

```json
{"version": "1.0.1"}
```

## 2.1 Instalador para otra PC

El instalador es un único ejecutable que instala la aplicación, crea los accesos directos y registra el desinstalador.

1. Ejecuta `build.bat` en la carpeta principal para generar `dist\RegistroTaximetros.exe`.
2. Ejecuta `instalador\build_instalador.bat`.
3. Se crea `instalador\Output\InstalarRegistroTaximetros.exe` (unos 35 MB).
4. Copia **ese único archivo** a la otra PC y ejecútalo.

Por defecto instala en `%LOCALAPPDATA%\Programs\RegistroTaximetros`, sin pedir permisos de administrador. Durante la instalación puedes elegir otra carpeta, crear accesos en el escritorio y en el menú Inicio, y abrir la aplicación al terminar.

Para desinstalar, usa el acceso *Desinstalar* del menú Inicio o *Aplicaciones y características*. Los registros de ventas se conservan por defecto; el desinstalador ofrece borrarlos también.

## 3. Configurar las actualizaciones desde GitHub

### 3.1 Crear el repositorio

1. Crea un repositorio en GitHub (por ejemplo `RegistroTaximetros`).
2. Sube esta carpeta completa, incluida `.github\workflows\release.yml`.
3. En el repositorio, ve a **Settings → Actions → General → Workflow permissions** y activa **Read and write permissions**. Es necesario para que el workflow pueda crear releases.

### 3.2 Configurar el programa instalado

La forma más sencilla es abrir **Archivo → Configuración de actualizaciones** (o el botón **⚙ Configuración** del menú lateral). Allí puedes cambiar:

- **Usuario u organización (owner)** y **repositorio** de GitHub.
- **URL de latest.json** (opcional): si la rellenas, se usa esa dirección en vez de la de GitHub. Sirve para servidores propios.
- **Archivo de la release** (`asset_name`, valor de respaldo).
- **Comprobación automática**: activarla o desactivarla.
- **Intervalo**: cada cuántos minutos se revisa si hay versión nueva (de 5 a 1440).

El botón **Probar conexión** descarga `latest.json` con los datos escritos y muestra la versión encontrada, sin guardar primero. Al guardar, los cambios se escriben en `actualizaciones.json` junto al `.exe` y se reprograman las comprobaciones al instante.

También puedes editar el archivo a mano a partir del ejemplo:

```json
{
  "owner": "TU_USUARIO_DE_GITHUB",
  "repo": "TU_REPOSITORIO",
  "asset_name": "RegistroTaximetros.exe",
  "latest_url": "",
  "auto_check": true,
  "check_interval_minutes": 60
}
```

Sin este archivo el programa funciona con normalidad, pero el menú **Ayuda → Buscar actualizaciones** indicará que no está configurado.

### 3.3 Publicar una versión nueva

Cada vez que subas un tag que empiece por `v`, GitHub Actions compila la app y el instalador versionado, calcula su SHA256, genera `latest.json` y crea una release con estos archivos:

- `RegistroTaximetros.exe`
- `RegistroTaximetros.exe.sha256`
- `RegistroTaximetrosSetup-1.0.1.exe`
- `latest.json`

```bat
git add .
git commit -m "Versión 1.0.1"
git tag v1.0.1
git push origin main
git push origin v1.0.1
```

`latest.json` queda disponible en:

```
https://github.com/USUARIO/REPO/releases/latest/download/latest.json
```

y tiene este formato:

```json
{
  "version": "1.0.1",
  "url": "RegistroTaximetrosSetup-1.0.1.exe",
  "sha256": "...",
  "notes": "Correcciones y mejoras"
}
```

El campo `url` puede ser solo el nombre del archivo (se resuelve contra la misma release) o una URL completa. El SHA256 se calcula en Windows con `Get-FileHash`; en una PC también puedes verificarlo con `certutil -hashfile "instalador.exe" SHA256`.

### 3.4 Cómo se ve la actualización para el usuario

- Al abrir el programa se comprueba silenciosamente `latest.json`. Después se repite cada `check_interval_minutes` mientras la comprobación automática esté activada.
- Si hay versión nueva, **se descarga en segundo plano sin bloquear la venta**: solo aparece el porcentaje en la barra de estado.
- Al terminar, se valida el SHA256. Si coincide, aparece un **banner no modal** con **Instalar ahora** y **Más tarde**. Puedes seguir registrando ventas mientras tanto.
- Si eliges **Más tarde**, el instalador queda guardado en `datos\actualizaciones\` y el aviso vuelve a aparecer al reiniciar.
- Al pulsar **Instalar ahora**, la app se cierra, se ejecuta el instalador de forma silenciosa sobre la carpeta actual y la aplicación se abre de nuevo.
- Si el hash no coincide, la descarga se descarta y el banner ofrece **Reintentar**.
- Si estás ejecutando desde Python (no desde el `.exe`), el instalador se guarda en `datos\actualizaciones\` y se muestra su ruta para ejecutarlo manualmente.

La comparación de versiones usa el campo `version` de `latest.json`, por ejemplo `1.0.1`. Usa siempre formato `N.N.N`.

## 4. Datos y copias de seguridad

La base de datos se crea en:

```
< carpeta del programa >\datos\ventas.sqlite3
```

Si la carpeta del programa no permite escribir (por ejemplo, instalado en Archivos de programa), se usa:

```
%LOCALAPPDATA%\RegistroTaximetros\datos\ventas.sqlite3
```

Para hacer una copia, basta con cerrar el programa y copiar `ventas.sqlite3`. También puedes usar **Exportar CSV** para obtener un archivo legible desde Excel.

## 5. Solución de problemas

| Situación | Solución |
|---|---|
| "No se pudo comprobar actualizaciones" | Revisa conexión a internet, la URL de `latest.json` (o usuario/repo) y que el repo sea público o accesible. |
| "latest.json no indica el instalador" | El campo `url` de `latest.json` debe contener el nombre del instalador o una URL completa. |
| "La suma de verificación SHA256 no coincide" | La descarga se descartó. Vuelve a intentarlo; si persiste, revisa el workflow de GitHub y que `sha256` corresponda al instalador publicado. |
| `git` no está instalado en tu PC | No hace falta para ejecutar el programa: el workflow de GitHub compila en la nube. Para publicar tags necesitarás Git o crear la release desde la web. |
| El instalador no se aplica | Revisa `datos\actualizacion.log`. Asegúrate de no tener otra instancia abierta. |

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

Junto al `.exe`, crea un archivo llamado `actualizaciones.json` a partir del ejemplo:

```json
{
  "owner": "TU_USUARIO_DE_GITHUB",
  "repo": "TU_REPOSITORIO",
  "asset_name": "RegistroTaximetros.exe"
}
```

Sustituye `owner` y `repo` por los tuyos. Sin este archivo el programa funciona con normalidad, pero el menú **Ayuda → Buscar actualizaciones** indicará que no está configurado.

### 3.3 Publicar una versión nueva

Cada vez que subas un tag que empiece por `v`, GitHub Actions compila el `.exe`, calcula su SHA256, genera el instalador y crea una release con los tres archivos:

```bat
git add .
git commit -m "Versión 1.0.1"
git tag v1.0.1
git push origin main
git push origin v1.0.1
```

También puedes crear la release manualmente desde la web de GitHub. La condición indispensable es que el asset se llame exactamente `RegistroTaximetros.exe` (o el nombre que pusiste en `asset_name`).

### 3.4 Cómo se ve la actualización para el usuario

- Al abrir el programa se comprueba silenciosamente si hay versión nueva. Si la hay, se muestra un aviso en la barra de estado.
- El menú **Ayuda → Buscar actualizaciones** permite comprobar manualmente y descargar.
- La descarga muestra una barra de progreso y valida el SHA256 si la release incluye el archivo `RegistroTaximetros.exe.sha256`.
- Al aceptar, el programa se cierra, reemplaza el ejecutable y se abre de nuevo automáticamente.
- Si estás ejecutando desde Python (no desde el `.exe`), la descarga se guarda en `datos\actualizaciones\` y se ofrece abrir la carpeta para reemplazar el archivo manualmente.

La comparación de versiones se hace con el tag de la release, por ejemplo `v1.0.1`. Usa siempre formato `vN.N.N`.

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
| "No se pudo comprobar actualizaciones" | Revisa conexión a internet, el usuario/repo en `actualizaciones.json` y que el repo sea público o accesible. |
| "La release no incluye el archivo..." | El nombre del asset debe coincidir con `asset_name`. |
| "La suma de verificación SHA256 no coincide" | La descarga se descartó. Vuelve a intentarlo; si persiste, revisa el workflow de GitHub. |
| `git` no está instalado en tu PC | No hace falta para ejecutar el programa: el workflow de GitHub compila en la nube. Para publicar tags necesitarás Git o crear la release desde la web. |
| El .exe no se reemplaza | Revisa `datos\actualizacion.log`. Asegúrate de no tener otra instancia abierta. |

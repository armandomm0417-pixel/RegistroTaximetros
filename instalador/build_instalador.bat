@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "..\dist\RegistroTaximetros.exe" (
    echo Falta ..\dist\RegistroTaximetros.exe
    echo Ejecuta primero build.bat en la carpeta RegistroVentas.
    pause
    exit /b 1
)

if not exist "..\actualizaciones.json" (
    echo Falta ..\actualizaciones.json
    pause
    exit /b 1
)

echo ============================================
echo  Compilando instalador
echo ============================================
echo.

echo [1/2] Desinstalador...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name DesinstalarRegistroTaximetros ^
  desinstalador.py
if errorlevel 1 goto error

echo [2/2] Instalador...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name InstalarRegistroTaximetros ^
  --add-data "..\dist\RegistroTaximetros.exe;." ^
  --add-data "..\actualizaciones.json;." ^
  --add-data "dist\DesinstalarRegistroTaximetros.exe;." ^
  instalador.py
if errorlevel 1 goto error

if not exist Output mkdir Output
move /Y "dist\InstalarRegistroTaximetros.exe" "Output\InstalarRegistroTaximetros.exe" >nul

echo.
echo Listo: "%~dp0Output\InstalarRegistroTaximetros.exe"
echo Copia ese unico archivo a la otra PC y ejecutalo.
echo.
pause
exit /b 0

:error
echo.
echo Error al compilar el instalador.
pause
exit /b 1

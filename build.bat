@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  Construyendo RegistroTaximetros.exe
echo ============================================
echo.

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name RegistroTaximetros ^
  --add-data "version.json;." ^
  main.py

if errorlevel 1 (
    echo.
    echo Error al construir. Revisa el mensaje anterior.
    pause
    exit /b 1
)

echo.
echo Listo: "%~dp0dist\RegistroTaximetros.exe"
echo Copia ese exe y actualizaciones.json en la carpeta donde quieras instalarlo.
echo.
pause

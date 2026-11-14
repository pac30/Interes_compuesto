@echo off
REM Genera FinMathLab.exe junto a app.py usando un entorno virtual temporal.
REM Requiere Python 3.10.1 o superior (3.10.0 tiene un error que rompe PyInstaller).
set VENV=%TEMP%\finmath_build_venv
if not exist "%VENV%\Scripts\python.exe" python -m venv "%VENV%"
"%VENV%\Scripts\python.exe" -m pip install -q flask openpyxl reportlab python-dateutil pyinstaller
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --name FinMathLab --add-data "web\templates;web\templates" --add-data "web\static;web\static" app.py
copy /Y dist\FinMathLab.exe FinMathLab.exe
rmdir /S /Q build dist
del FinMathLab.spec
echo Listo: FinMathLab.exe
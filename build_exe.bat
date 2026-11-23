@echo off
REM Genera FinMathLab.exe junto a app.py usando un entorno virtual temporal.
REM Requiere Python 3.10.1 o superior (3.10.0 tiene un error que rompe PyInstaller).
set VENV=%TEMP%\finmath_build_venv
if exist "%VENV%" rmdir /S /Q "%VENV%"
py -3.12 -m venv "%VENV%" || python -m venv "%VENV%" || goto :error
"%VENV%\Scripts\python.exe" -m pip install -q flask openpyxl reportlab python-dateutil pyinstaller || goto :error
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --name FinMathLab --add-data "web\templates;web\templates" --add-data "web\static;web\static" app.py || goto :error
copy /Y dist\FinMathLab.exe FinMathLab.exe || goto :error
rmdir /S /Q build dist
if exist FinMathLab.spec del FinMathLab.spec
echo Listo: FinMathLab.exe
exit /b 0
:error
echo ERROR: no se pudo generar FinMathLab.exe
exit /b 1

@echo off
TITLE RenForge 2.0 Launcher
CLS
ECHO ===================================================
ECHO RenForge 2.0 Baslatiliyor...
ECHO ===================================================
ECHO.

:: 1. Python Kontrolu (python komutu)
ECHO [1/3] Python kontrol ediliyor...
python --version 2>NUL
IF %ERRORLEVEL% EQU 0 (
    ECHO Python bulundu:
    python --version
    GOTO :START_APP
)

:: 2. Python Kontrolu (py komutu - Windows Launcher)
ECHO 'python' komutu bulunamadi, 'py' komutu deneniyor...
py --version 2>NUL
IF %ERRORLEVEL% EQU 0 (
    ECHO Python Launcher bulundu:
    py --version
    SET PYTHON_CMD=py
    GOTO :START_APP_PY
)

:: Hata: Python yok
COLOR 0C
ECHO.
ECHO [HATA] Python bulunamadi!
ECHO Lutfen Python'un yuklu oldugundan ve PATH'e eklendiginden emin olun.
ECHO.
PAUSE
EXIT /B

:START_APP
ECHO.
ECHO [2/3] Uygulama baslatiliyor (python main.py)...
ECHO ---------------------------------------------------
python main.py
GOTO :END

:START_APP_PY
ECHO.
ECHO [2/3] Uygulama baslatiliyor (py main.py)...
ECHO ---------------------------------------------------
py main.py
GOTO :END

:END
ECHO ---------------------------------------------------
ECHO.
ECHO [3/3] Uygulama kapandi.
ECHO.
PAUSE

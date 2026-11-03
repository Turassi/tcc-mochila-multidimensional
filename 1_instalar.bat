@echo off
cd /d "%~dp0"
echo ============================================
echo  PASSO 1 - Instalacao das bibliotecas
echo ============================================
py --version
if errorlevel 1 goto sempython
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
if errorlevel 1 goto erro
echo.
echo Instalacao concluida. Proximo passo: 2_rodar_experimento.bat
pause
exit /b
:sempython
echo.
echo ERRO: Python nao encontrado. Instale o Python 3.10 ou superior - veja o LEIA-ME.
pause
exit /b
:erro
echo.
echo ERRO na instalacao das bibliotecas. Verifique a conexao com a internet.
pause

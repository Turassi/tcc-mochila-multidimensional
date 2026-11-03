@echo off
cd /d "%~dp0"
echo ============================================
echo  PASSO 3 - Tabelas, testes estatisticos e graficos
echo ============================================
py analise.py
if errorlevel 1 goto erro
echo.
echo Concluido. Os arquivos estao na pasta resultados.
start "" "%~dp0resultados"
pause
exit /b
:erro
echo.
echo ERRO na analise. Verifique se o passo 2 foi executado.
pause

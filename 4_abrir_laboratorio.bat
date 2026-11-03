@echo off
cd /d "%~dp0"
echo ============================================
echo  Laboratorio da Mochila Multidimensional
echo  Mantenha esta janela aberta durante o uso.
echo ============================================
py -c "import tkinter" 2>nul
if errorlevel 1 goto semtk
py laboratorio.py
if errorlevel 1 goto erro
exit /b
:semtk
echo.
echo ERRO: a instalacao do Python nao inclui o modulo tkinter - interface grafica.
pause
exit /b
:erro
echo.
echo ERRO ao abrir o laboratorio. Verifique a mensagem acima.
pause

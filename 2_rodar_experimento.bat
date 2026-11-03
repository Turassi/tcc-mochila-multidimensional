@echo off
cd /d "%~dp0"
echo ============================================
echo  PASSO 2 - Experimento completo
echo  2 algoritmos x 23 instancias x 30 execucoes
echo  Duracao: de 1 a 3 horas, conforme o computador.
echo  Se for interrompido, rode novamente: ele
echo  continua de onde parou.
echo ============================================
py experimento.py
if errorlevel 1 goto erro
echo.
echo Experimento concluido. Proximo passo: 3_gerar_analise.bat
pause
exit /b
:erro
echo.
echo ERRO durante o experimento. Verifique a mensagem acima.
pause

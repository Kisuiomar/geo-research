@echo off
chcp 65001 > nul
echo =======================================================
echo Открытие порта 8765 в Windows Firewall для GeoSleuth
echo =======================================================
netsh advfirewall firewall add rule name="GeoSleuth Intelligence Hub (Port 8765)" dir=in action=allow protocol=TCP localport=8765
if %ERRORLEVEL% EQU 0 (
    echo [УСПЕХ] Порт 8765 успешно открыт в брандмауэре Windows!
    echo Теперь другие компьютеры и телефоны могут заходить по адресу:
    echo http://192.168.68.51:8765
) else (
    echo [ОШИБКА] Запустите этот файл правой кнопкой мыши -> "Запуск от имени администратора"!
)
echo.
pause

 @echo off
cd /d "C:\Weat_ejem"

:: Prepara todos los archivos actualizados (html, jpg, etc.)
git add .

:: Guarda los cambios usando la fecha y hora actual como mensaje
git commit -m "Actualizacion automatica: %date% %time%"

:: Sube los archivos reemplazando la version previa en GitHub
git push origin main
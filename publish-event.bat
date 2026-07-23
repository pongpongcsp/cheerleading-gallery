@echo off
REM One-shot publish for a single local event folder into cheerleading-gallery.
REM Usage:
REM   publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩"

setlocal
set "SOURCE=%~1"
set "FOLDER=%~2"
set "MAX_KEEPERS=%~3"

if "%SOURCE%"=="" goto usage
if "%FOLDER%"=="" goto usage
if "%MAX_KEEPERS%"=="" set "MAX_KEEPERS=50"

if not exist "%SOURCE%" (
  echo Source folder not found: %SOURCE%
  exit /b 1
)

if not exist ".env" (
  echo Missing .env — copy .env.example to .env and fill Cloudinary credentials.
  exit /b 1
)

set "CULL_OUT=culling\%FOLDER%"
set "COMPRESSED=compressed\%FOLDER%"

echo === 1/4 Cull top %MAX_KEEPERS% ===
python tools\cull-photos.py "%SOURCE%" "%CULL_OUT%" --max-keepers %MAX_KEEPERS% --copy-keepers
if errorlevel 1 exit /b 1

echo === 2/4 Compress keepers ===
python tools\compress-photos.py "%CULL_OUT%\keepers" "%COMPRESSED%" --quality 85 --max-edge 2000
if errorlevel 1 exit /b 1

echo === 3/4 Upload to Cloudinary folder "%FOLDER%" ===
node tools\upload-to-cloudinary.js "%COMPRESSED%" "%FOLDER%"
if errorlevel 1 exit /b 1

echo === 4/4 Generate js\photos.js ===
echo Ensure tools\gallery-folders.json includes folder=%FOLDER%
node tools\generate-photos.js
if errorlevel 1 exit /b 1

echo.
echo Done. Review culling\%FOLDER%\culling-report.html, then:
echo   git add js\photos.js tools\gallery-folders.json
echo   git commit -m "Publish %FOLDER%"
echo   git push
exit /b 0

:usage
echo Usage: publish-event.bat "SOURCE_FOLDER" "CLOUDINARY_FOLDER" [max_keepers]
echo Example: publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩" 50
exit /b 1

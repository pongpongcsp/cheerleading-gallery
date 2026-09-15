@echo off
REM One-shot publish for a single local event folder into cheerleading-gallery.
REM Usage:
REM   publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩"
REM   publish-event.bat "D:\Photo\..." "folder" [max_keepers]
REM Optional 3rd arg max_keepers: omit or 0 = uncapped (PixCull keep).
REM Flow: Cull → Manual confirm → Compress → Upload → Generate

setlocal
set "SOURCE=%~1"
set "FOLDER=%~2"
set "MAX_KEEPERS=%~3"

if "%SOURCE%"=="" goto usage
if "%FOLDER%"=="" goto usage
if "%MAX_KEEPERS%"=="" set "MAX_KEEPERS=0"

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
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

if "%MAX_KEEPERS%"=="0" (
  echo === 1/5 Cull ^(uncapped, PixCull keep^) ===
) else (
  echo === 1/5 Cull top %MAX_KEEPERS% ===
)
"%PY%" tools\cull-photos.py "%SOURCE%" "%CULL_OUT%" --max-keepers %MAX_KEEPERS% --copy-keepers
if errorlevel 1 exit /b 1

echo.
echo === 2/5 Manual confirm ===
echo Review: %CULL_OUT%\culling-report.html
echo Keepers: %CULL_OUT%\keepers
echo Delete unwanted files from keepers\ if needed, then continue.
if exist "%CULL_OUT%\culling-report.html" start "" "%CULL_OUT%\culling-report.html"
choice /C YN /M "Continue to compress"
if errorlevel 2 (
  echo Skipped compress/upload for %FOLDER%.
  exit /b 0
)

echo === 3/5 Compress keepers ===
"%PY%" tools\compress-photos.py "%CULL_OUT%\keepers" "%COMPRESSED%" --quality 85 --max-edge 2000
if errorlevel 1 exit /b 1

echo === 4/5 Upload to Cloudinary folder "%FOLDER%" ===
node tools\upload-to-cloudinary.js "%COMPRESSED%" "%FOLDER%"
if errorlevel 1 exit /b 1

echo === 5/5 Generate js\photos.js ===
echo Ensure tools\gallery-folders.json includes folder=%FOLDER%
node tools\generate-photos.js
if errorlevel 1 exit /b 1

echo.
echo Done. Then:
echo   git add js\photos.js tools\gallery-folders.json
echo   git commit -m "Publish %FOLDER%"
echo   git push
exit /b 0

:usage
echo Usage: publish-event.bat "SOURCE_FOLDER" "CLOUDINARY_FOLDER" [max_keepers]
echo Example: publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩"
echo Optional max_keepers: omit or 0 = uncapped PixCull keep decisions
echo Flow: Cull → Manual confirm → Compress → Upload → Generate
exit /b 1

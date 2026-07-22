@echo off
REM One-shot publish for a local event folder into cheerleading-gallery.
REM Usage:
REM   publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩" competition "桃園 樂天女孩"

setlocal
set "SOURCE=%~1"
set "FOLDER=%~2"
set "CATEGORY=%~3"
set "LABEL=%~4"

if "%SOURCE%"=="" goto usage
if "%FOLDER%"=="" goto usage
if "%CATEGORY%"=="" set "CATEGORY=competition"
if "%LABEL%"=="" set "LABEL=%FOLDER%"

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

echo === 1/4 Cull ===
python tools\cull-photos.py "%SOURCE%" "%CULL_OUT%" --copy-keepers
if errorlevel 1 exit /b 1

echo === 2/4 Compress keepers ===
python tools\compress-photos.py "%CULL_OUT%\keepers" "%COMPRESSED%" --quality 85 --max-edge 2000
if errorlevel 1 exit /b 1

echo === 3/4 Upload to Cloudinary folder "%FOLDER%" ===
node tools\upload-to-cloudinary.js "%COMPRESSED%" "%FOLDER%"
if errorlevel 1 exit /b 1

echo === 4/4 Generate js\photos.js ===
echo Make sure tools\gallery-folders.json includes:
echo   folder=%FOLDER%  category=%CATEGORY%  categoryLabel=%LABEL%
node tools\generate-photos.js
if errorlevel 1 exit /b 1

echo.
echo Done. Review the site locally, then:
echo   git add js\photos.js tools\gallery-folders.json
echo   git commit -m "Publish %FOLDER%"
echo   git push
exit /b 0

:usage
echo Usage: publish-event.bat "SOURCE_FOLDER" "CLOUDINARY_FOLDER" [category] [categoryLabel]
echo Example: publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩" competition "桃園 樂天女孩"
exit /b 1

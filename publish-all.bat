@echo off
REM Batch publish all events in tools\gallery-folders.json
REM (~50 keepers each → compress → Cloudinary → generate js\photos.js)
REM
REM Usage:
REM   publish-all.bat
REM   publish-all.bat --skip-upload
REM   publish-all.bat --only 20250928_桃園_樂天女孩
REM   publish-all.bat --photo-root "D:\Photo"

setlocal
cd /d "%~dp0"

if not exist ".env" (
  echo Missing .env — copy .env.example to .env and fill Cloudinary credentials.
  echo Or pass --skip-upload to only cull+compress.
)

echo Publishing events from tools\gallery-folders.json ...
node tools\publish-events.js %*
if errorlevel 1 exit /b 1

echo.
echo Done. Spot-check culling\*\culling-report.html then:
echo   git add js\photos.js tools\gallery-folders.json index.html
echo   git commit -m "Publish culled event galleries"
echo   git push
exit /b 0

@echo off
chcp 65001 >nul
echo ============================================
echo   mp4togif — 打包为独立 .exe
echo ============================================
echo.

pyinstaller --onefile --windowed ^
  --name "MP4toGIF" ^
  --add-data "ffmpeg.exe;." ^
  --add-data "ffprobe.exe;." ^
  --icon=NONE ^
  mp4togif_modern.py

echo.
echo ============================================
echo   打包完成! 输出在 dist\MP4toGIF.exe
echo ============================================
pause

@echo off
chcp 65001 >nul
echo ============================================
echo   视频转GIF — 打包为独立 .exe
echo ============================================
echo.

pyinstaller --onefile --windowed ^
  --name "视频转GIF" ^
  --add-data "ffmpeg.exe;." ^
  --add-data "ffprobe.exe;." ^
  --icon="2.ico" ^
  mp4togif_modern.py

echo.
echo ============================================
echo   打包完成! 输出在 dist\视频转GIF.exe
echo ============================================
pause

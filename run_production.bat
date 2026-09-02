@echo off
title NetWatch Enterprise Network Monitoring System
echo ==============================================================================
echo    NETWATCH - ENTERPRISE NETWORK MONITORING & AUTOMATION PLATFORM
echo ==============================================================================
echo.
echo  Starting Production Multi-Threaded WSGI Server...
echo.

cd /d "%~dp0\backend"
..\backend\.venv\Scripts\python.exe server.py

pause

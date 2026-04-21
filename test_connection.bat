@echo off
cd /d "%~dp0"
echo Running Azure connection test...
python test_connection.py

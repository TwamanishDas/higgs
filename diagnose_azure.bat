@echo off
cd /d "%~dp0"
echo Running Azure AI Foundry diagnostics...
python diagnose_azure.py

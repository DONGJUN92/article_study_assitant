@echo off
echo Starting OpenDataLoader PDF Hybrid Backend Server...
echo Make sure you have activated the virtual environment!
call venv\Scripts\activate.bat
opendataloader-pdf-hybrid --port 5002

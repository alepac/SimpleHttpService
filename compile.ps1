.venv\Scripts\python .\create_version.py -o version.txt -v (type version.py) -n SimpleHttpService
pyinstaller.exe --onefile --hidden-import win32timezone --version-file version.txt SimpleHttpServer.py
iscc SimpleHttpServer.iss
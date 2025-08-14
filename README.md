sc create SimpleHttpServer binpath= C:\Users\Leonardo\Documents\Projects\SimpleHttpServer\dist\SimpleHttpServer.exe
sc delete SimpleHttpServer

# Build with powershell:
.venv\Scripts\python .\create_version.py -o version.txt -v (type version.py) -n SimpleHttpService
pyinstaller.exe --onefile --hidden-import win32timezone SimpleHttpServer.py

# With Administrator privilges
# Install:
dist\SimpleHttpServer.exe install

# Start:
dist\SimpleHttpServer.exe start

# Install with autostart:
dist\SimpleHttpServer.exe --startup delayed install

# Debug:
dist\SimpleHttpServer.exe debug

# Stop:
dist\SimpleHttpServer.exe stop

# Uninstall:
dist\SimpleHttpServer.exe remove
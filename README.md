sc create SimpleHttpServer binpath= C:\Users\Leonardo\Documents\Projects\SimpleHttpServer\dist\SimpleHttpServer.exe
sc delete SimpleHttpServer

# Build:
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
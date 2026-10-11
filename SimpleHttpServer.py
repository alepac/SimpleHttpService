import http.server
import configparser
import threading
from threading import Event
import logging
import os
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import secrets
import sqlite3
from http.cookies import CookieError, SimpleCookie
from datetime import datetime
from urllib.parse import parse_qs, urlsplit
import version
import json

from Cinema import Cinema
from ThreadingHTTPServerWithArgs import ThreadingHTTPServerWithArgs

default_values = {
    "httpPort": 8000,
    "httpAddress": "0.0.0.0",
    "corsAllowedOrigins": "http://localhost:5173"
}

current_dir = os.path.dirname(sys.executable)
web_folder = current_dir + '\\public'
log_folder = current_dir + '\\log'
serviceLogger = logging.getLogger(__name__)

serviceLogger.setLevel(logging.DEBUG)


class SessionStore:
    def __init__(self):
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._connection.execute(
                "CREATE TABLE sessions (session_id TEXT PRIMARY KEY, cinema_id TEXT NOT NULL)"
            )

    def is_valid(self, cinema, session_id):
        with self._lock:
            result = self._connection.execute(
                "SELECT 1 FROM sessions WHERE cinema_id = ? AND session_id = ?",
                (cinema, session_id)
            ).fetchone()
        return result is not None

    def create(self, cinema, session_id):
        with self._lock:
            self._connection.execute(
                "INSERT INTO sessions (session_id, cinema_id) VALUES (?, ?)",
                (session_id, cinema)
            )
            self._connection.commit()

    def delete(self, cinema, session_id):
        with self._lock:
            self._connection.execute(
                "DELETE FROM sessions WHERE cinema_id = ? AND session_id = ?",
                (cinema, session_id)
            )
            self._connection.commit()


class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    # Override the __init__ method to specify the directory
    def __init__(self, request, client_address, server, *args, **kwargs):
        # Questi sono gli argomenti aggiuntivi che passerai al server, qui li estraiamo.
        self.cinema_instances = kwargs.pop('cinema_instances', {})
        self._pending_session_cookie = None
        
        # Ora passiamo tutti gli argomenti al costruttore della classe base.
        super().__init__(request, client_address, server, directory=web_folder, *args, **kwargs)    
    
    def log_message(self, format, *args):
        serviceLogger.info(format % args)
        
    def end_headers(self):
        # Aggiunge l'header CORS a ogni risposta (GET, POST, ecc.)
        origin = self.headers.get('Origin')
        if origin in self.server.cors_allowed_origins:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, X-Requested-With')
            self.send_header('Vary', 'Origin')
        if self._pending_session_cookie is not None:
            cookie_name, session_id = self._pending_session_cookie
            if session_id is None:
                self.send_header(
                    'Set-Cookie',
                    f'{cookie_name}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax'
                )
            else:
                self.send_header(
                    'Set-Cookie',
                    f'{cookie_name}={session_id}; Path=/; HttpOnly; SameSite=Lax'
                )
            self._pending_session_cookie = None
        super().end_headers()
    
    def do_OPTIONS(self):
        # Risponde alla richiesta preflight del browser
        self.send_response(200, "ok")
        self.end_headers()
        
    def checkAuth(self, cinema):
        cookie_name = self._session_cookie_name(cinema)
        session_id = self._get_session_id(cookie_name)
        if session_id is not None and self.server.session_store.is_valid(cinema, session_id):
            return True

        auth_header = self.headers.get('Authorization')
        if auth_header != self.cinema_instances[cinema]._password:
            self.send_response(401) # 401 Unauthorized
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "error", "msg": "Accesso negato: password errata"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return False

        session_id = secrets.token_urlsafe(32)
        self.server.session_store.create(cinema, session_id)
        self._pending_session_cookie = (cookie_name, session_id)
        return True

    def _get_session_id(self, cookie_name):
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get('Cookie', ''))
        except CookieError:
            return None
        session_cookie = cookies.get(cookie_name)
        return session_cookie.value if session_cookie is not None else None

    def _session_cookie_name(self, cinema):
        return f'session_{cinema}'
    
    def getCinema(self):
                # Controlla se l'URL richiesto è quello della nostra pagina dinamica
        cinema = None
        service = None
        try:
            cinema, service = urlsplit(self.path).path[1:].split('/')[:2] 
        except Exception as e:
            pass
        return cinema, service
        
    def do_POST(self):
        
        cinema, service = self.getCinema() 
        if cinema not in self.cinema_instances:
            self.send_error(404)
            return

        if service == 'logout':
            cookie_name = self._session_cookie_name(cinema)
            session_id = self._get_session_id(cookie_name)
            if session_id is not None:
                self.server.session_store.delete(cinema, session_id)
            self._pending_session_cookie = (cookie_name, None)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')
            return

        if not self.checkAuth(cinema):
            return
        
        if cinema in  self.cinema_instances:
            if service == 'force_update':
                self.cinema_instances[cinema].forceDownload()
                self.send_response(201) # 201 Created è standard per le POST
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response = {"status": "success"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            elif service == 'set_param':
                # 2. Leggi la lunghezza del corpo della richiesta
                content_length = int(self.headers.get('Content-Length', 0))
                
                # 3. Leggi i dati dal buffer
                post_data = self.rfile.read(content_length)
                
                try:
                    data = post_data.decode('utf-8')
                    # 4. Decodifica i byte in stringa e poi in JSON (dizionario Python)
                    self.cinema_instances[cinema].setParamsJson(data)
                    
                    
                    # 5. Risposta al client
                    self.send_response(201) # 201 Created è standard per le POST
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    
                    response = {"status": "success", "received": data}
                    self.wfile.write(json.dumps(response).encode('utf-8'))

                except json.JSONDecodeError:
                    # Se il corpo non è un JSON valido
                    self.send_response(400) # Bad Request
                    self.end_headers()
                    self.wfile.write(b'{"status": "error", "message": "Invalid JSON"}')
            else:
                self.send_response(400) # Bad Request
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Invalid request"}')
        
    def do_GET(self):
        if self.path == '/version':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(f"SimpleHttpService: {version.SIMPLEHTTPSERVICE_VERSION}", "utf8"))
            return
        # Controlla se l'URL richiesto è quello della nostra pagina dinamica
        cinema, service = self.getCinema() 
        query = parse_qs(urlsplit(self.path).query)
        ignore_matinee_filter = query.get('ignoreMatineeFilter', ['false'])[0].lower() == 'true'
        if cinema in  self.cinema_instances:
            # Prepara e invia la risposta per la pagina dinamica

            if self.path.endswith('dashboard'):
                self.send_response(302)
            
                self.send_header('Location', self.path + '/')
                self.end_headers()
            elif service == "get_param":
                if not self.checkAuth(cinema):
                    return
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(self.cinema_instances[cinema].getParamsJson(), "utf8"))
            elif service == "dashboard":
                # Path override
                path = urlsplit(self.path).path
                parts = [p for p in path.split('/') if p]
                ends = '/' if path.endswith('/') else ''
                self.path = '/' + '/'.join(parts[1:]) + ends
                super().do_GET()
            else:
                self.send_response(200)
                if service == "films_json":
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(bytes(self.cinema_instances[cinema].getFilmsJson(), "utf8"))
                elif service == "db": # legacy... to mantain for backward compatibility
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps(self.cinema_instances[cinema].getDbJson(ignore_matinee_filter)), "utf8"))
                elif service == "db_config":
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps(self.cinema_instances[cinema].getDbConfigJson(ignore_matinee_filter)), "utf8"))
                else:
                    self.send_header('Content-type', 'text/xml')
                    self.end_headers()
                    if service == "films":
                        self.wfile.write(bytes(self.cinema_instances[cinema].getFilmsXml(), "utf8"))
                    elif service == "sale":
                        self.wfile.write(bytes(self.cinema_instances[cinema].getSaleXml(), "utf8"))
                    else: 
                        super().do_GET()
        else:
            # Per tutte le altre richieste, usa il comportamento predefinito
            super().do_GET()

class SimpleHttpService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'SimpleHttpService'
    _svc_display_name_ = 'Simple Http Service'
    _svc_description_ = 'It serves simple http requests'

    def __init__(self, args):
        self.log = serviceLogger
        try:            
            args_list = list(args)
            if not(len(args_list) > 1 and args_list[1].lower() == 'standalone'):
                win32serviceutil.ServiceFramework.__init__(self, args)
                self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

            socket.setdefaulttimeout(60)
            self.cinema_data_managers = {}
            self.stop_event = Event()
            self.start_event = Event()
            self.session_store = SessionStore()
        except Exception as e:
            self.log.error(f"Exception initializing SimpleHttpService: {e}")


    def SvcStop(self):
        self.log.info(f"Stopping service v{version.SIMPLEHTTPSERVICE_VERSION}")
        self.stop_event.set()
        try:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.server.shutdown()
            win32event.SetEvent(self.hWaitStop)
            self.log.info(f'Server stopped')
        except Exception as e:
            self.log.exception(e)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, 
                              servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ''))

        daily_log_handler_thread = threading.Thread(target=self.Schedule_daily_log_handler)
        daily_log_handler_thread.start()
        self.start_event.wait()
        self.log.info(f"Starting service v{version.SIMPLEHTTPSERVICE_VERSION}")
        self.Run()
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
    
    def Create_daily_log_handler(self):
        today = datetime.today()
        if not os.path.exists(log_folder):
            os.mkdir(log_folder)
        log_filename = today.strftime(log_folder +'\\http_server_%Y-%m-%d.log')
        fileHandler = logging.FileHandler(log_filename)
        fileHandler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)-7.7s %(message)s'))
        for handler in self.log.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                self.log.removeHandler(handler)
                handler.close()
        self.log.addHandler(fileHandler)

    def Schedule_daily_log_handler(self):
        first_run=True
        while not self.stop_event.is_set():
            self.Create_daily_log_handler()
            if first_run:
                self.start_event.set()
                first_run=False
            current_time = datetime.now()
            midnight = datetime(year=current_time.year, month=current_time.month, day=current_time.day, hour=23, minute=59, second=59)
            time_to_midnight = midnight - current_time
            seconds_until_midnight = time_to_midnight.total_seconds() + 2
            self.stop_event.wait(timeout=seconds_until_midnight)

    def Run(self):
        config = configparser.ConfigParser(default_values)
        config.read(current_dir + '\\config.ini')

        httpPort = int(config['DEFAULT']['httpPort'])
        httpAddress = config['DEFAULT']['httpAddress']
        cors_allowed_origins = {
            origin.strip()
            for origin in config['DEFAULT']['corsAllowedOrigins'].split(',')
            if origin.strip()
        }
        
        for section in config.sections():
            if not section.startswith('DEFAULT'):
                id = section
                password = config[section]['password']
                numero_sale = int(config[section]['numero_sale'])
                films_url = config[section]['films_url']
                sale_url = config[section]['sale_url']
                name = config[section]['name']
                films_interval = int(config[section]['films_interval'])
                sale_interval = int(config[section]['sale_interval'])
                self.cinema_data_managers[id] = Cinema(
                    id = id, 
                    name = name, 
                    films_url=films_url, 
                    sale_url=sale_url, 
                    logger=serviceLogger, 
                    films_interval=films_interval, 
                    sale_interval=sale_interval, 
                    db_file=current_dir + '\\cinema_' + id,
                    password=password,
                    numero_sale=numero_sale)
        
        # Avvia i thread di polling
        for cinema_managed in self.cinema_data_managers.values():
            cinema_managed.start()

        while not self.stop_event.is_set():
            try:
                self.server = ThreadingHTTPServerWithArgs(
                    (httpAddress, httpPort),
                    MyRequestHandler,
                    self.cinema_data_managers,
                    self.session_store,
                    cors_allowed_origins
                )
                self.log.info(f'Serving on interface {httpAddress} port {httpPort} from "{web_folder}"')
                self.server.serve_forever()
            except Exception as e:
                self.log.info(f"Error starting HTTP server: {e}")
                self.stop_event.set()
        for cinema_managed in self.cinema_data_managers.values():
            cinema_managed.stop()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(SimpleHttpService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception:
            win32serviceutil.HandleCommandLine(SimpleHttpService)
    elif sys.argv[1].lower() == 'standalone':
        # Run the service in standalone mode
        web_folder = 'public'
        current_dir = '.'
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)-7.7s %(message)s')
        serviceLogger.info("Running in standalone mode")
        service = SimpleHttpService(sys.argv)
        service.Run()
    else:
        win32serviceutil.HandleCommandLine(SimpleHttpService)

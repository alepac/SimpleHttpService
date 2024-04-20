import http.server
import configparser
import threading
import logging
import os
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import sys
from datetime import datetime
default_values = {
    "httpPort": 8000
}

current_dir = os.path.dirname(sys.executable)
web_folder = current_dir + '\public'
log_folder = current_dir + '\log'
serviceLogger = logging.getLogger(__name__)

def create_daily_log_handler():
    today = datetime.today()
    if not os.path.exists(log_folder):
        os.mkdir(log_folder)
    log_filename = today.strftime(log_folder +'\http_server_%Y-%m-%d.log')
    fileHandler = logging.FileHandler(log_filename)
    fileHandler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)-7.7s %(message)s'))
    for handler in serviceLogger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            serviceLogger.removeHandler(handler)
            handler.close()
    serviceLogger.addHandler(fileHandler)

serviceLogger.setLevel(logging.DEBUG)


def schedule_daily_log_handler():
    while True:
        create_daily_log_handler()
        time.sleep(60*60*24)

daily_log_handler_thread = threading.Thread(target=schedule_daily_log_handler)
daily_log_handler_thread.start()

class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    # Override the __init__ method to specify the directory
    def __init__(self, request, address, server):
        super().__init__(request, address, server, directory=web_folder)    
    
    def log_message(self, format, *args):
        serviceLogger.info(format % args)

class SimpleHttpService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'SimpleHttpService'
    _svc_display_name_ = 'Simple Http Service'
    _svc_description_ = 'It serves simple http requests'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.log = serviceLogger

        socket.setdefaulttimeout(60)
        self.isAlive = True

    def SvcStop(self):
        self.log.info("Stopping service")
        try:
            self.isAlive = False
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.log.info(f'Server stopping')
            self.server.shutdown()
            win32event.SetEvent(self.hWaitStop)
            self.log.info(f'Server stopped')
        except Exception as e:
            self.log.exception(e)

    def SvcDoRun(self):
        self.isAlive = True
        self.log.info("Starting service")
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, 
                              servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ''))
        self.Run()
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def Run(self):
        config = configparser.ConfigParser(default_values)
        config.read(current_dir + '\config.ini')

        httpPort = int(config['DEFAULT']['httpPort'])

        while self.isAlive:
            try:
                self.server = http.server.ThreadingHTTPServer(('localhost', httpPort), MyRequestHandler)
                self.log.info(f'Serving on port {httpPort} from "{web_folder}"')
                self.server.serve_forever()
            except Exception as e:
                self.log.info(f"Error starting HTTP server: {e}")
                self.isAlive = False

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SimpleHttpService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SimpleHttpService)






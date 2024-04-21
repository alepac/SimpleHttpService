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
import time
import sys
from datetime import datetime

VERSION="0.0.1"

default_values = {
    "httpPort": 8000
}

current_dir = os.path.dirname(sys.executable)
web_folder = current_dir + '\public'
log_folder = current_dir + '\log'
serviceLogger = logging.getLogger(__name__)

serviceLogger.setLevel(logging.DEBUG)

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
        self.stop_event = Event()
        self.start_event = Event()



    def SvcStop(self):
        self.log.info(f"Stopping service v{VERSION}")
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
        self.log.info(f"Starting service v{VERSION}")
        self.Run()
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
    
    def Create_daily_log_handler(self):
        today = datetime.today()
        if not os.path.exists(log_folder):
            os.mkdir(log_folder)
        log_filename = today.strftime(log_folder +'\http_server_%Y-%m-%d.log')
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
        config.read(current_dir + '\config.ini')

        httpPort = int(config['DEFAULT']['httpPort'])

        while not self.stop_event.is_set():
            try:
                self.server = http.server.ThreadingHTTPServer(('localhost', httpPort), MyRequestHandler)
                self.log.info(f'Serving on port {httpPort} from "{web_folder}"')
                self.server.serve_forever()
            except Exception as e:
                self.log.info(f"Error starting HTTP server: {e}")
                self.stop_event.set()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(SimpleHttpService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception:
            win32serviceutil.HandleCommandLine(SimpleHttpService)
    else:
        win32serviceutil.HandleCommandLine(SimpleHttpService)






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

default_values = {
    "httpPort": 8000
}

current_dir = os.path.dirname(sys.executable)

logging.basicConfig(
    filename = current_dir + '\log\SimpleHttpService.log',
    level = logging.DEBUG, 
    format = '[SimpleHttpService] %(levelname)-7.7s %(message)s'
)

class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    # Override the __init__ method to specify the directory
    def __init__(self, request, address, server):
        super().__init__(request, address, server, directory=current_dir + '\public')    

class SimpleHttpService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'SimpleHttpService'
    _svc_display_name_ = 'Simple Http Service'
    _svc_description_ = 'It serves simple http requests'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.log = logging.getLogger(__name__)

        socket.setdefaulttimeout(60)
        self.isAlive = True

    def SvcStop(self):
        self.log.info("Stopping service")

        self.isAlive = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        self.isAlive = True
        self.log.info("Starting service")
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, 
                              servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ''))
        self.Run()
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def main(self):
        while self.isAlive:
            self.log.info(f'''Running on {current_dir}''')
            time.sleep(10)

    def Run(self):
        config = configparser.ConfigParser(default_values)
        config.read(current_dir + '\config.ini')

        httpPort = int(config['DEFAULT']['httpPort'])

        while self.isAlive:
            try:
                self.server = http.server.ThreadingHTTPServer(('localhost', httpPort), MyRequestHandler)
                self.log.info(f'Serving on port {httpPort}')
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






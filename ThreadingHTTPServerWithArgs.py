import http.server
import socketserver

# Incolla qui la tua classe MyRequestHandler e la tua classe Cinema
# ... (codice delle classi MyRequestHandler e Cinema) ...


class ThreadingHTTPServerWithArgs(socketserver.ThreadingMixIn, http.server.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, cinema_instances):
        super().__init__(server_address, RequestHandlerClass)
        self.cinema_instances = cinema_instances
    
    def finish_request(self, request, client_address):
        # Questo metodo viene chiamato per ogni richiesta.
        # Qui instanziamo il RequestHandler e gli passiamo gli argomenti extra.
        self.RequestHandlerClass(request, client_address, self, cinema_instances=self.cinema_instances)
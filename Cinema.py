import json
import xml.etree.ElementTree as ET
import time
import threading
import requests
import logging

class Cinema:
    """
    Una classe per gestire il polling di un URL JSON, convertirlo in XML e renderlo disponibile.
    """
    def __init__(self, http_url, logger, interval=10):
        """
        Inizializza l'istanza della classe.

        :param http_url: L'URL HTTP da cui leggere il JSON.
        :param logger: Un'istanza del logger da utilizzare per i messaggi.
        :param interval: L'intervallo di tempo in secondi tra una richiesta e l'altra.
        """
        self.http_url = http_url
        self.logger = logger
        self.interval = interval
        self._content = None
        self._thread = None
        self._running = False
        self._lock = threading.Lock()

    def _convert_json_to_rss(self, json_data):
        """
        Converte un JSON con un array di film in un feed RSS 2.0.
        """
        try:
            root = ET.Element("rss", version="2.0")
            channel = ET.SubElement(root, "channel")
            
            # Aggiungi i metadati del canale
            title = ET.SubElement(channel, "title")
            title.text = "Eliminacode"
            description = ET.SubElement(channel, "description")
            description.text = "Questa pagina è un eliminacode"
            
            # Itera sull'array di film nel JSON
            films = json_data.get("films", [])
            for film in films:
                # Per ogni film, crea un nuovo elemento <item>
                item = ET.SubElement(channel, "item")
                
                # Aggiungi i campi del film come elementi XML
                for key, value in film.items():
                    # Ignora il campo 'film_occupation' come richiesto
                    if key == "film_occupations":
                        element = ET.SubElement(item, key)
                        count = 0
                        for occupation in value:
                            occupationElement = ET.SubElement(element, f"occupation_{count}")
                            count = count + 1
                            for subkey, subvalue in occupation.items():
                                subelement = ET.SubElement(occupationElement, subkey)
                                subelement.text = str(subvalue)
                    else:
                        # Crea un tag XML con il nome del campo
                        element = ET.SubElement(item, key)
                        
                        # Converti il valore in stringa e assegnaglielo come testo
                        element.text = str(value)
            
            # Restituisci il contenuto XML come stringa formattata
            return ET.tostring(root, encoding='unicode')

        except Exception as e:
            self.logger.error(f"Errore durante la conversione da JSON a RSS: {e}")
            # Restituisci un XML di errore in caso di fallimento
            return f'<rss><channel><item><error>{e}</error></item></channel></rss>'


    def _poll_data(self):
        """
        Il metodo che verrà eseguito nel thread separato.
        Effettua la richiesta HTTP, converte la risposta in XML e aggiorna la variabile.
        """
        while self._running:
            try:
                response = requests.get(self.http_url, timeout=5)
                response.raise_for_status()  # Solleva un'eccezione per errori HTTP (4xx o 5xx)
                
                json_data = response.json()
                xml_data = self._convert_json_to_rss(json_data)
                
                with self._lock:
                    self._content = xml_data
                
                self.logger.info(f"Dati aggiornati dall'URL: {self.http_url}")
                
            except requests.exceptions.RequestException as e:
                error_message = f"Errore durante la richiesta HTTP all'URL {self.http_url}: {e}"
                self.logger.error(error_message)
                with self._lock:
                    self._content = f"<error>{error_message}</error>"
            except json.JSONDecodeError:
                error_message = f"Errore di decodifica JSON dalla risposta dell'URL {self.http_url}"
                self.logger.error(error_message)
                with self._lock:
                    self._content = f"<error>{error_message}</error>"
            except Exception as e:
                error_message = f"Errore generico durante il polling: {e}"
                self.logger.error(error_message)
                with self._lock:
                    self._content = f"<error>{error_message}</error>"

            time.sleep(self.interval)

    def start(self):
        """
        Avvia il thread di polling.
        """
        if self._thread is None or not self._thread.is_alive():
            self._running = True
            self._thread = threading.Thread(target=self._poll_data, daemon=True)
            self._thread.start()
            self.logger.info("Thread di polling avviato.")
        else:
            self.logger.warning("Il thread è già in esecuzione.")

    def stop(self):
        """
        Arresta il thread di polling.
        """
        if self._thread and self._thread.is_alive():
            self._running = False
            self._thread.join()
            self.logger.info("Thread di polling arrestato.")
        else:
            self.logger.warning("Il thread non è in esecuzione.")

    def getContent(self):
        """
        Restituisce il contenuto XML aggiornato.
        """
        with self._lock:
            return self._content
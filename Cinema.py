import json
import xml.etree.ElementTree as ET
import time
import threading
import requests
import logging

from datetime import datetime
from zoneinfo import ZoneInfo

def parse_iso_datetime(iso_str):
    try:
        # Parsing della stringa ISO
        dt = datetime.fromisoformat(iso_str)

        # Conversione alla timezone locale
        mytime = datetime.now().astimezone()
        local_tz = mytime.tzinfo
        dt_local = dt.astimezone(local_tz)

        # Estrazione di data e ora come stringhe
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%H:%M:%S")
        diff_minutes = int((dt_local - mytime).total_seconds() / 60)


        return date_str, time_str, diff_minutes
    except ValueError:
        return None, None, None  # La stringa non è in formato ISO valido


class Cinema:
    """
    Una classe per gestire il polling di un URL JSON, convertirlo in XML e renderlo disponibile.
    """
    def __init__(self, name, films_url, sale_url, logger, interval=10):
        """
        Inizializza l'istanza della classe.

        :param http_url: L'URL HTTP da cui leggere il JSON.
        :param logger: Un'istanza del logger da utilizzare per i messaggi.
        :param interval: L'intervallo di tempo in secondi tra una richiesta e l'altra.
        """
        self.films_url = films_url
        self.sale_url = sale_url
        self.name = name
        self.logger = logger
        self.interval = interval
        self._films_content = None
        self._sale_content = None
        self._content = None
        self._thread = None
        self._running = False
        self._lock = threading.Lock()

    def _append_rss_elements(self, name, json_data, parent):
        if isinstance(json_data, list):
            for data in json_data:
                item = ET.SubElement(parent, name)
                self._append_rss_elements(name, data, item)
        elif isinstance(json_data, dict):
            for key, value in json_data.items():
                self._append_rss_elements(key,value,parent)
        else:
            text = str(json_data)
            date, time, delta = parse_iso_datetime(text)
            if date and time:
                element = ET.SubElement(parent, name+"_date")            
                element.text = str(date)
                element = ET.SubElement(parent, name+"_time")            
                element.text = str(time)
                element = ET.SubElement(parent, name+"_delta")            
                element.text = str(delta)
            else:
                element = ET.SubElement(parent, name)            
                element.text = str(json_data)


    def _convert_dict_to_rss(self, json_data, main):
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
            data = json_data.get(main, [])
            self._append_rss_elements( 'item', data, channel)
            # for film in films:
            #     # Per ogni film, crea un nuovo elemento <item>
            #     item = ET.SubElement(channel, "item")
                
            #     # Aggiungi i campi del film come elementi XML
            #     for key, value in film.items():
            #         # Ignora il campo 'film_occupation' come richiesto
            #         if key == "film_occupations":
            #             element = ET.SubElement(item, key)
            #             count = 0
            #             for occupation in value:
            #                 occupationElement = ET.SubElement(element, f"occupation_{count}")
            #                 count = count + 1
            #                 for subkey, subvalue in occupation.items():
            #                     subelement = ET.SubElement(occupationElement, subkey)
            #                     subelement.text = str(subvalue)
            #         else:
            #             # Crea un tag XML con il nome del campo
            #             element = ET.SubElement(item, key)
                        
            #             # Converti il valore in stringa e assegnaglielo come testo
            #             element.text = str(value)
            
            # Restituisci il contenuto XML come stringa formattata
            return ET.tostring(root, encoding='unicode')

        except Exception as e:
            self.logger.error(f"Errore durante la conversione da JSON a RSS: {e}")
            # Restituisci un XML di errore in caso di fallimento
            return f'<rss><channel><item><error>{e}</error></item></channel></rss>'

    def _poll_data(self, http_url):
        try:
            response = requests.get(http_url, timeout=5)
            response.raise_for_status()  # Solleva un'eccezione per errori HTTP (4xx o 5xx)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_message = f"Errore durante la richiesta HTTP all'URL {http_url}: {e}"
            self.logger.error(error_message)
            return f"<error>{error_message}</error>"
        except json.JSONDecodeError:
            error_message = f"Errore di decodifica JSON dalla risposta dell'URL {http_url}"
            self.logger.error(error_message)
            return f"<error>{error_message}</error>"
        except Exception as e:
            error_message = f"Errore generico durante il polling: {e}"
            self.logger.error(error_message)
            return f"<error>{error_message}</error>"

    def _poll_thread(self):
        """
        Il metodo che verrà eseguito nel thread separato.
        Effettua la richiesta HTTP, converte la risposta in XML e aggiorna la variabile.
        """

        while self._running:
            data = self._poll_data(self.films_url)
            xml_data = self._convert_dict_to_rss(data, 'films')
            with self._lock:
                self._films_content = xml_data
                self._content = json.dumps(data)          
            self.logger.info(f"Dati aggiornati dall'URL: {self.films_url}")
            xml_data = self._convert_dict_to_rss(self._poll_data(self.sale_url), self.name)
            with self._lock:
                self._sale_content = xml_data            
            self.logger.info(f"Dati aggiornati dall'URL: {self.sale_url}")

            time.sleep(self.interval)

    def start(self):
        """
        Avvia il thread di polling.
        """
        if self._thread is None or not self._thread.is_alive():
            self._running = True
            self._thread = threading.Thread(target=self._poll_thread, daemon=True)
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
        Restituisce il contenuto JSON aggiornato.
        """
        with self._lock:
            return self._content

    def getFilmContent(self):
        """
        Restituisce il contenuto XML aggiornato.
        """
        with self._lock:
            return self._films_content
        
    def getSaleContent(self):
        """
        Restituisce il contenuto XML aggiornato.
        """
        with self._lock:
            return self._sale_content
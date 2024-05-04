#! -*- encoding: utf8 -*-
import heapq as hq

from typing import Tuple, List, Optional, Dict, Union

import requests
import bs4
import re
from urllib.parse import urljoin
import json
import math
import os

class SAR_Wiki_Crawler:

    def __init__(self):
        # Expresión regular para detectar si es un enlace de la Wikipedia
        self.wiki_re = re.compile(r"(http(s)?:\/\/(es)\.wikipedia\.org)?\/wiki\/[\w\/_\(\)\%]+")
        # Expresión regular para limpiar anclas de editar
        self.edit_re = re.compile(r"\[(editar)\]")
        # Formato para cada nivel de sección
        self.section_format = {
            "h1": "##{}##",
            "h2": "=={}==",
            "h3": "--{}--"
        }

        # Expresiones regulares útiles para el parseo del documento
        #coje y divide en title el titulo summary lo de abajo y todo el resto en una seccion llamada rest
        self.title_sum_re = re.compile(r"##(?P<title>.+)##\n(?P<summary>((?!==.+==).+|\n)+)(?P<rest>(.+|\n)*)")
        #todos los titulos de las secciones de las paginas
        self.sections_re = re.compile(r"==.+==\n")
        #hace lo mismo que el primero pero en lugar de con la pagina con secciones hace las mismas 3 divisiones
        self.section_re = re.compile(r"==(?P<name>.+)==\n(?P<text>((?!--.+--).+|\n)*)(?P<rest>(.+|\n)*)")
        #saca los titulos de las subsecciones
        self.subsections_re = re.compile(r"--.+--\n")
        #divide en titulo y texto cada una de las subsecciones
        self.subsection_re = re.compile(r"--(?P<name>.+)--\n(?P<text>(.+|\n)*)")


    def is_valid_url(self, url: str) -> bool:
        """Verifica si es una dirección válida para indexar

        Args:
            url (str): Dirección a verificar

        Returns:
            bool: True si es valida, en caso contrario False
        """
        return self.wiki_re.fullmatch(url) is not None


    def get_wikipedia_entry_content(self, url: str) -> Optional[Tuple[str, List[str]]]:
        """Devuelve el texto en crudo y los enlaces de un artículo de la wikipedia

        Args:
            url (str): Enlace a un artículo de la Wikipedia

        Returns:
            Optional[Tuple[str, List[str]]]: Si es un enlace correcto a un artículo
                de la Wikipedia en inglés o castellano, devolverá el texto y los
                enlaces que contiene la página.

        Raises:
            ValueError: En caso de que no sea un enlace a un artículo de la Wikipedia
                en inglés o español
        """
        if not self.is_valid_url(url):
            raise ValueError((
                f"El enlace '{url}' no es un artículo de la Wikipedia en español"
            ))

        try:
            req = requests.get(url)
        except Exception as ex:
            print(f"ERROR: - {url} - {ex}")
            return None


        # Solo devolvemos el resultado si la petición ha sido correcta
        if req.status_code == 200:
            soup = bs4.BeautifulSoup(req.text, "lxml")
            urls = set()

            for ele in soup.select((
                'div#catlinks, div.printfooter, div.mw-authority-control'
            )):
                ele.decompose()

            # Recogemos todos los enlaces del contenido del artículo
            for a in soup.select("div#bodyContent a", href=True):
                href = a.get("href")
                if href is not None:
                    urls.add(href)

            # Contenido del artículo
            content = soup.select((
                "h1.firstHeading,"
                "div#mw-content-text h2,"
                "div#mw-content-text h3,"
                "div#mw-content-text h4,"
                "div#mw-content-text p,"
                "div#mw-content-text ul,"
                "div#mw-content-text li,"
                "div#mw-content-text span"
            ))

            dedup_content = []
            seen = set()

            for element in content:
                if element in seen:
                    continue

                dedup_content.append(element)

                # Añadimos a vistos, tanto el elemento como sus descendientes
                for desc in element.descendants:
                    seen.add(desc)

                seen.add(element)

            text = "\n".join(
                self.section_format.get(element.name, "{}").format(element.text)
                for element in dedup_content
            )

            # Eliminamos el texto de las anclas de editar
            text = self.edit_re.sub('', text)

            return text, sorted(list(urls))

        return None


    def parse_wikipedia_textual_content(self, text: str, url: str) -> Optional[Dict[str, Union[str,List]]]:
        """Devuelve una estructura tipo artículo a partir del text en crudo

        Args:
            text (str): Texto en crudo del artículo de la Wikipedia
            url (str): url del artículo, para añadirlo como un campo

        Returns:

            Optional[Dict[str, Union[str,List[Dict[str,Union[str,List[str,str]]]]]]]:

            devuelve un diccionario con las claves 'url', 'title', 'summary', 'sections':
                Los valores asociados a 'url', 'title' y 'summary' son cadenas,
                el valor asociado a 'sections' es una lista de posibles secciones.
                    Cada sección es un diccionario con 'name', 'text' y 'subsections',
                        los valores asociados a 'name' y 'text' son cadenas y,
                        el valor asociado a 'subsections' es una lista de posibles subsecciones
                        en forma de diccionario con 'name' y 'text'.

            en caso de no encontrar título o resúmen del artículo, devolverá None

        """

        def clean_text(txt):
            return '\n'.join(l for l in txt.split('\n') if len(l) > 0)

        document = None

        text = clean_text(text)         #Eliminamos lineas en blanco
        diccionario = {'url': '',
                       'title': '',
                       'summary': '',
                       'sections': []
                      }
        
        diccionario['url'] = url
        partes = self.title_sum_re.match(text)       #Sacamos el titulo, resumen y los apartados

        if partes:
            diccionario['title'] = partes.group('title')  #Si no esta vacio asigna el match de titulo con el titulo del diccionario
            diccionario["summary"] = partes.group('summary')  #Si no esta vacio asigna el match del resumen con el resumen del diccionario
            secciones = partes.group('rest')                  #Si no esta vacio asigna el match de rest con una var secciones que seguiremos desglosando
            print("Dado el Texto:\n"+text+"\n")

            start_indices = []                                  #Creamos una lista de indices de inicio de secciones
            for coinc in self.sections_re.finditer(secciones):
                start= coinc.start() 
                
                start_indices.append(start)

            for i in range(len(start_indices)):                #Para cada indice de inicio de seccion 

                if (i+1) >= len(start_indices):                   #Si el indice siguiente es mayor que la longitud de la lista de indices
                    section = secciones[start_indices[i]:]
                else:
                    section = secciones[start_indices[i]:start_indices[i+1]] 
               
               
                dic = self.section_re.match(section).groupdict()   
                nombre, texto, sub_secciones = dic['name'], dic['text'], dic['rest']  #Sacamos el nombre, texto y subsecciones de cada match
                seccion_dict = {'name': nombre, 'text': texto, 'subsections': []}
                
                start_indices_sub = []
                for coinc in self.subsection_re.finditer(sub_secciones):
                    start = coinc.start()
                    start_indices_sub.append(start)
                
                for j in range(len(start_indices_sub)):
                    if (j+1) >= len(start_indices_sub):
                        subsection = sub_secciones[start_indices_sub[j]:]
                    else:
                        subsection = sub_secciones[start_indices_sub[j]:start_indices_sub[j+1]]
                    
                    dic_sub = self.subsection_re.match(subsection).groupdict()
                    nombre_sub, texto_sub = dic_sub['name'], dic_sub['text']
                    subseccion_dict = {'name': nombre_sub, 'text': texto_sub}
                    seccion_dict['subsections'].append(subseccion_dict)
                
                diccionario['sections'].append(seccion_dict)
        print("Obtenemos el diccionario:")

        return diccionario


    def save_documents(self,
        documents: List[dict], base_filename: str,
        num_file: Optional[int] = None, total_files: Optional[int] = None
    ):
        """Guarda una lista de documentos (text, url) en un fichero tipo json lines
        (.json). El nombre del fichero se autogenera en base al base_filename,
        el num_file y total_files. Si num_file o total_files es None, entonces el
        fichero de salida es el base_filename.

        Args:
            documents (List[dict]): Lista de documentos.
            base_filename (str): Nombre base del fichero de guardado.
            num_file (Optional[int], optional):
                Posición numérica del fichero a escribir. (None por defecto)
            total_files (Optional[int], optional):
                Cantidad de ficheros que se espera escribir. (None por defecto)
        """
        assert base_filename.endswith(".json")

        if num_file is not None and total_files is not None:
            # Separamos el nombre del fichero y la extensión
            base, ext = os.path.splitext(base_filename)
            # Padding que vamos a tener en los números
            padding = len(str(total_files))

            out_filename = f"{base}_{num_file:0{padding}d}_{total_files}{ext}"

        else:
            out_filename = base_filename

        with open(out_filename, "w", encoding="utf-8", newline="\n") as ofile:
            for doc in documents:
                print(json.dumps(doc, ensure_ascii=True), file=ofile)


    def start_crawling(self, 
                    initial_urls: List[str], document_limit: int,
                    base_filename: str, batch_size: Optional[int], max_depth_level: int,
                    ):        
         

        """Comienza la captura de entradas de la Wikipedia a partir de una lista de urls válidas, 
            termina cuando no hay urls en la cola o llega al máximo de documentos a capturar.
        
        Args:
            initial_urls: Direcciones a artículos de la Wikipedia
            document_limit (int): Máximo número de documentos a capturar
            base_filename (str): Nombre base del fichero de guardado.
            batch_size (Optional[int]): Cada cuantos documentos se guardan en
                fichero. Si se asigna None, se guardará al finalizar la captura.
            max_depth_level (int): Profundidad máxima de captura.
        """

        # URLs válidas, ya visitadas (se hayan procesado, o no, correctamente)
        visited = set()
        # URLs en cola
        to_process = set(initial_urls)
        # direcciones a visitar hacemos esta tripleta para amrcar la profundidad
        # y tener en cuenta la url lo de en medio es la url del padre que en nivel 0 no hay
        queue = [(0, "", url) for url in to_process]

        # haciendo uso de queue y la profundidad hace el montículo
        hq.heapify(queue)
        # buffer de documentos capturados
        documents: List[dict] = []
        # contador del número de documentos capturados(para no excedernos)
        total_documents_captured = 0
        # contador del número de ficheros escritos
        files_count = 0
        

        # en caso de que no utilicemos bach_size, asignamos None a total_files
        # así el guardado no modificará el nombre del fichero base
        if batch_size is None:
            total_files = None
        else:
            # Suponemos que vamos a poder alcanzar el límite para la nomenclatura
            # de guardado
            total_files = math.ceil(document_limit / batch_size)

        # COMPLETAR
        # asegurarnos que no se exceda
        bdepth = 1
        # pararemos si vaciamos la cola(poco prob) o si excedemos el numero de documentos
        while queue and total_documents_captured < document_limit and bdepth:
            depth, parent_url, current_url = hq.heappop(queue)
            
            if depth > max_depth_level:
                bdepth = 0
                continue
            
            if current_url in visited:
                continue

            # marcar la url como visitada
            visited.add(current_url)
            # punto 2 descargamos el contenido
            content, urls = self.get_wikipedia_entry_content(current_url)

            #añadimos cada url como bien dice en el punto 3. la visiitaremos luego
            for url in urls:
                full_url = urljoin(current_url, url)
                if self.is_valid_url(full_url) and full_url not in visited:
                    # ahora ya hay padre hay que tenerlo en cuenta, asi como la profundidad
                    hq.heappush(queue, (depth + 1, current_url, full_url))

            # procesamos el contenido textual p.4
            if content:
                # hacemos uso de nuestro metodo para que saque el diccionario con la info
                article = self.parse_wikipedia_textual_content(content, current_url)
                if article:
                    documents.append(article)
                    total_documents_captured += 1
                    # guardar documentos en batches si está definido batch_size
                    if batch_size and len(documents) >= batch_size:
                        # método recomendado
                        self.save_documents(documents, base_filename, files_count + 1, total_files)
                        # limpiamos para volver a llenar
                        documents = []
                        files_count += 1



        # guardar los documentos restantes si no se han guardado por no cumpliarse aun el if
        if documents:
            self.save_documents(documents, base_filename, files_count + 1, total_files)
        

    def wikipedia_crawling_from_url(self,
        initial_url: str, document_limit: int, base_filename: str,
        batch_size: Optional[int], max_depth_level: int
    ):
        """Captura un conjunto de entradas de la Wikipedia, hasta terminar
        o llegar al máximo de documentos a capturar.
        
        Args:
            initial_url (str): Dirección a un artículo de la Wikipedia
            document_limit (int): Máximo número de documentos a capturar
            base_filename (str): Nombre base del fichero de guardado.
            batch_size (Optional[int]): Cada cuantos documentos se guardan en
                fichero. Si se asigna None, se guardará al finalizar la captura.
            max_depth_level (int): Profundidad máxima de captura.
        """
        if not self.is_valid_url(initial_url) and not initial_url.startswith("/wiki/"):
            raise ValueError(
                "Es necesario partir de un artículo de la Wikipedia en español"
            )

        self.start_crawling(initial_urls=[initial_url], document_limit=document_limit, base_filename=base_filename,
                            batch_size=batch_size, max_depth_level=max_depth_level)



    def wikipedia_crawling_from_url_list(self,
        urls_filename: str, document_limit: int, base_filename: str,
        batch_size: Optional[int]
    ):
        """A partir de un fichero de direcciones, captura todas aquellas que sean
        artículos de la Wikipedia válidos

        Args:
            urls_filename (str): Lista de direcciones
            document_limit (int): Límite máximo de documentos a capturar
            base_filename (str): Nombre base del fichero de guardado.
            batch_size (Optional[int]): Cada cuantos documentos se guardan en
                fichero. Si se asigna None, se guardará al finalizar la captura.

        """

        urls = []
        with open(urls_filename, "r", encoding="utf-8") as ifile:
            for url in ifile:
                url = url.strip()

                # Comprobamos si es una dirección a un artículo de la Wikipedia
                if self.is_valid_url(url):
                    if not url.startswith("http"):
                        raise ValueError(
                            "El fichero debe contener URLs absolutas"
                        )

                    urls.append(url)

        urls = list(set(urls)) # eliminamos posibles duplicados

        self.start_crawling(initial_urls=urls, document_limit=document_limit, base_filename=base_filename,
                            batch_size=batch_size, max_depth_level=0)





if __name__ == "__main__":
    raise Exception(
        "Esto es una librería y no se puede usar como fichero ejecutable"
    )

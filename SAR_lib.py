import json
from nltk.stem.snowball import SnowballStemmer
import os
import re
import sys
import math
from pathlib import Path
from typing import Optional, List, Union, Dict
import pickle
import urllib.parse


class SAR_Indexer:
    """
    Prototipo de la clase para realizar la indexacion y la recuperacion de artículos de Wikipedia
        
        Preparada para todas las ampliaciones:
          parentesis + multiples indices + posicionales + stemming + permuterm

    Se deben completar los metodos que se indica.
    Se pueden añadir nuevas variables y nuevos metodos
    Los metodos que se añadan se deberan documentar en el codigo y explicar en la memoria
    """

    # lista de campos, el booleano indica si se debe tokenizar el campo
    # NECESARIO PARA LA AMPLIACION MULTIFIELD
    fields = [
        ("all", True), ("title", True), ("summary", True), ("section-name", True), ('url', False),
    ]
    def_field = 'all'
    PAR_MARK = '%'
    # numero maximo de documento a mostrar cuando self.show_all es False
    SHOW_MAX = 10

    all_atribs = ['urls', 'index', 'sindex', 'ptindex', 'docs', 'weight', 'articles',
                  'tokenizer', 'stemmer', 'show_all', 'use_stemming']

    def __init__(self):
        """
        Constructor de la classe SAR_Indexer.
        NECESARIO PARA LA VERSION MINIMA

        Incluye todas las variables necesaria para todas las ampliaciones.
        Puedes añadir más variables si las necesitas 

        """
        self.urls = set()  # hash para las urls procesadas,
        self.index = {}  # hash para el indice invertido de terminos --> clave: termino, valor: posting list
        self.sindex = {}  # hash para el indice invertido de stems --> clave: stem, valor: lista con los terminos que tienen ese stem
        self.ptindex = {}  # hash para el indice permuterm.
        self.docs = {}  # diccionario de terminos --> clave: entero(docid),  valor: ruta del fichero.
        self.weight = {}  # hash de terminos para el pesado, ranking de resultados.
        self.articles = {}  # hash de articulos --> clave entero (artid), valor: la info necesaria para diferencia los artículos dentro de su fichero
        self.tokenizer = re.compile("\\W+")  # expresion regular para hacer la tokenizacion
        self.stemmer = SnowballStemmer('spanish')  # stemmer en castellano
        self.show_all = False  # valor por defecto, se cambia con self.set_showall()
        self.show_snippet = False  # valor por defecto, se cambia con self.set_snippet()
        self.use_stemming = False  # valor por defecto, se cambia con self.set_stemming()
        self.use_ranking = False  # valor por defecto, se cambia con self.set_ranking()



        self.max_art_doc = 0  # maximo numero de articulos en un documento

    ###############################
    ###                         ###
    ###      CONFIGURACION      ###
    ###                         ###
    ###############################

    def set_showall(self, v: bool):
        """

        Cambia el modo de mostrar los resultados.
        
        input: "v" booleano.

        UTIL PARA TODAS LAS VERSIONES

        si self.show_all es True se mostraran todos los resultados el lugar de un maximo de self.SHOW_MAX, no aplicable a la opcion -C

        """
        self.show_all = v

    def set_snippet(self, v: bool):
        """

        Cambia el modo de mostrar snippet.
        
        input: "v" booleano.

        UTIL PARA TODAS LAS VERSIONES

        si self.show_snippet es True se mostrara un snippet de cada noticia, no aplicable a la opcion -C

        """
        self.show_snippet = v

    def set_stemming(self, v: bool):
        """

        Cambia el modo de stemming por defecto.
        
        input: "v" booleano.

        UTIL PARA LA VERSION CON STEMMING

        si self.use_stemming es True las consultas se resolveran aplicando stemming por defecto.

        """
        self.use_stemming = v

    #############################################
    ###                                       ###
    ###      CARGA Y GUARDADO DEL INDICE      ###
    ###                                       ###
    #############################################

    def save_info(self, filename: str):
        """
        Guarda la información del índice en un fichero en formato binario
        
        """
        info = [self.all_atribs] + [getattr(self, atr) for atr in self.all_atribs]
        with open(filename, 'wb') as fh:
            pickle.dump(info, fh)

    def load_info(self, filename: str):
        """
        Carga la información del índice desde un fichero en formato binario
        
        """
        #info = [self.all_atribs] + [getattr(self, atr) for atr in self.all_atribs]
        with open(filename, 'rb') as fh:
            info = pickle.load(fh)
        atrs = info[0]
        for name, val in zip(atrs, info[1:]):
            setattr(self, name, val)

    ###############################
    ###                         ###
    ###   PARTE 1: INDEXACION   ###
    ###                         ###
    ###############################

    def already_in_index(self, article: Dict) -> bool:
        """

        Args:
            article (Dict): diccionario con la información de un artículo

        Returns:
            bool: True si el artículo ya está indexado, False en caso contrario
        """
        return article['url'] in self.urls

    def index_dir(self, root: str, **args):
        """
        
        Recorre recursivamente el directorio o fichero "root" 
        NECESARIO PARA TODAS LAS VERSIONES
        
        Recorre recursivamente el directorio "root"  y indexa su contenido
        los argumentos adicionales "**args" solo son necesarios para las funcionalidades ampliadas

        """
        self.multifield = args['multifield']
        self.positional = args['positional']
        # self.stemming = args['stem']
        self.set_stemming(args['stem'])
        self.permuterm = args['permuterm']

        file_or_dir = Path(root)

        if file_or_dir.is_file():
            # is a file
            if self.docs is None:
                self.docs = {}
            self.docs[file_or_dir] = root
            self.index_file(file_or_dir)
        elif file_or_dir.is_dir():
            # is a directory
            for d, _, files in os.walk(root):
                for filename in sorted(files):
                    if filename.endswith('.json'):
                        fullname = os.path.join(d, filename)
                        if self.docs is None:
                            self.docs = {}
                        self.docs[fullname] = root
                        self.index_file(fullname)
        else:
            print(f"ERROR:{root} is not a file nor directory!", file=sys.stderr)
            sys.exit(-1)

        # Llamada a make_stemming si la opción de stemming está activa
        if self.use_stemming:
            self.make_stemming()

        # Llamada a make_permuterm si la opción de permuterm está activa
        if self.permuterm:
            self.make_permuterm()
        ##########################################
        ## COMPLETAR PARA FUNCIONALIDADES EXTRA ##
        ##########################################

    def parse_article(self, raw_line: str) -> Dict[str, str]:
        """
        Crea un diccionario a partir de una linea que representa un artículo del crawler

        Args:
            raw_line: una linea del fichero generado por el crawler

        Returns:
            Dict[str, str]: claves: 'url', 'title', 'summary', 'all', 'section-name'
        """

        article = json.loads(raw_line)
        sec_names = []
        txt_secs = ''
        for sec in article['sections']:
            txt_secs += sec['name'] + '\n' + sec['text'] + '\n'
            txt_secs += '\n'.join(
                subsec['name'] + '\n' + subsec['text'] + '\n' for subsec in sec['subsections']) + '\n\n'
            sec_names.append(sec['name'])
            sec_names.extend(subsec['name'] for subsec in sec['subsections'])
        article.pop('sections')  # no la necesitamos
        article['all'] = article['title'] + '\n\n' + article['summary'] + '\n\n' + txt_secs
        article['section-name'] = '\n'.join(sec_names)

        return article

    def index_file(self, filename: str):
        """

        Indexa el contenido de un fichero.
        
        input: "filename" es el nombre de un fichero generado por el Crawler cada línea es un objeto json
            con la información de un artículo de la Wikipedia

        NECESARIO PARA TODAS LAS VERSIONES

        dependiendo del valor de self.multifield y self.positional se debe ampliar el indexado


        """
        max_v = 0
        for i, line in enumerate(open(filename)):
            j = self.parse_article(line)
            max_v += 1

            # para no indexar dos con la misma url(lo habiamos gestionado el el crawler)
            if self.already_in_index(j):
                continue

            self.urls.add(j['url'])

            #nos asegu5remos que los vamos a ir guardando en orden uno tras otro
            art_id = len(self.articles)
            self.articles[art_id] = (i, j['url'])

            #usaremos uno u otro dependiendo de si la funcion esta activa o no
            if self.multifield:
                fields_to_index = ['url', 'title', 'summary', 'all', 'section-name']
            else:
                fields_to_index = ['all']

                #ahora a diferencia de solo all tenmos que hacer la indexacion para cada podrible campo o solo all

            for field in fields_to_index:
                text = j[field]
                # quitar en las urls los https://es.wikipedia.org/wiki/
                if field == 'url':
                    tokens = [text]
                    # text = urllib.parse.unquote(text)
                    # text = text.replace('https://es.wikipedia.org/wiki/', '')
                else:
                    tokens = self.tokenize(text)

                for token in tokens:
                    if field not in self.index:
                        self.index[field] = {}
                    if token not in self.index[field]:
                        self.index[field][token] = []  #inicializamos su list si no lo estaba para ese token en ese field
                    if self.index[field][token] and self.index[field][token][-1] == art_id:
                        continue
                    self.index[field][token].append(art_id)  # como ya nos hemos asegurado appendeamos

        self.max_art_doc = max(max_v, self.max_art_doc)

        #
        # 
        # En la version basica solo se debe indexar el contenido "article"
        #
        #
        #
        #################
        ### COMPLETAR ###
        #################

    def set_stemming(self, v: bool):
        """

        Cambia el modo de stemming por defecto.
        
        input: "v" booleano.

        UTIL PARA LA VERSION CON STEMMING

        si self.use_stemming es True las consultas se resolveran aplicando stemming por defecto.

        """
        self.use_stemming = v

    def tokenize(self, text: str):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Tokeniza la cadena "texto" eliminando simbolos no alfanumericos y dividientola por espacios.
        Puedes utilizar la expresion regular 'self.tokenizer'.

        params: 'text': texto a tokenizar

        return: lista de tokens

        """
        return self.tokenizer.sub(' ', text.lower()).split()

    def make_stemming(self):
        """

        Crea el indice de stemming (self.sindex) para los terminos de todos los indices.

        NECESARIO PARA LA AMPLIACION DE STEMMING.

        "self.stemmer.stem(token) devuelve el stem del token"


        """

        # Asegurarse de que self.sindex está inicializado para cada campo
        for field in self.index.keys():
            if field not in self.sindex:
                self.sindex[field] = {}

        # Procesar cada campo en el índice
        for field, terms in self.index.items():
            for term in terms.keys():
                # Obtenemos el stem del término
                stem = self.stemmer.stem(term)

                # Si el stem no está en el índice de stemming, lo añade
                if stem not in self.sindex[field]:
                    self.sindex[field][stem] = []

                # Añade el término al stem correspondiente
                self.sindex[field][stem].append(term)

        ####################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA DE STEMMING ##
        ####################################################

    def make_permuterm(self):
        """

        Crea el indice permuterm (self.ptindex) para los terminos de todos los indices.

        NECESARIO PARA LA AMPLIACION DE PERMUTERM


        """

        # Asumiendo que self.index es un diccionario de diccionarios, donde el primer nivel de claves son los campos
        # y el segundo nivel son los términos con sus respectivas posting lists
        for field, terms in self.index.items():
            if field not in self.ptindex:
                self.ptindex[field] = {}  # Inicializa un diccionario para el campo si no existe
            for term in terms.keys():
                # Añade el símbolo de fin de cadena y crea permutaciones del término
                rotated_term = term + '$'
                # Creamos todas las permutaciones posibles del término
                for i in range(len(rotated_term)):
                    permuterm = rotated_term[i:] + rotated_term[:i]
                    # Guardamos la permutacion con referencia al término original
                    self.ptindex[field][permuterm] = term


        # print("Self.index", self.index)

        # for term in self.index:
        #     print(term)
        #     # añade el símbolo de fin de cadena y crea permutaciones del término
        #     rotated_term = term + '$'
        #     # haremos tantas como letras tenga
        #     for i in range(len(rotated_term)):
        #         permuterm = rotated_term[i:] + rotated_term[:i]
        #         # guardamos la permutacion con referencia al termino original
        #         self.ptindex[permuterm] = term  
        ####################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA DE STEMMING ##
        ####################################################

    def show_stats(self):
        """
        NECESARIO PARA TODAS LAS VERSIONES
        
        Muestra estadisticas de los indices
        
        """
        #italic in python

        print("=" * 40)
        print(f"Number of indexed files: {len(self.docs)}")
        print("-" * 40)
        print(f"Number of indexed articles: {len(self.articles)}")
        print("-" * 40)

        print("TOKENS:")

        if self.multifield:
            fields_to_index = ['all', 'title', 'summary', 'section-name', 'url']
            for field in fields_to_index:
                print(f"\t# of tokens in '{field}': {len(self.index[field])}")
        else:
            print(f"\t# of tokens in 'all': {len(self.index['all'])}")
        print("-" * 40)
        # print(self.ptindex)
        if self.permuterm:
            print("PERMUTERMS:")

            if self.multifield:
                fields_to_index = ['all', 'title', 'summary', 'section-name', 'url']
                for field in fields_to_index:
                    print(f"\t# of permuterms in '{field}': {len(self.ptindex[field])}")
            else:
                print(f"\t# of permuterms in 'all': {len(self.ptindex['all'])}")
            print("-" * 40)

        if self.use_stemming:
            print("STEMS:")

            if self.multifield:
                fields_to_index = ['all', 'title', 'summary', 'section-name', 'url']
                for field in fields_to_index:
                    print(f"\t# of stems in '{field}': {len(self.sindex[field])}")
            else:
                print(f"\t# of stems in 'all': {len(self.sindex['all'])}")
            print("-" * 40)
        # opciones en genral activadas
        # print("Opciones activadas:")
        # print(f"Stemming está {'activado' if self.use_stemming else 'desactivado'}.")
        # print(f"Multifield está {'activado' if self.multifield else 'desactivado'}.")
        # print(f"Permuterm está {'activado' if self.permuterm else 'desactivado'}.")
        # print(f"Ranking de resultados está {'activado' if self.use_ranking else 'desactivado'}.")

        # # num tot de documentos
        # print(f"Número de documentos indexados: {len(self.docs)}")

        # # indice general de terminos
        # num_terms = len(self.index)
        # print(f"Número de términos únicos en el índice invertido: {num_terms}")

        # # dicc del steaming
        # if self.sindex:
        #     num_stems = len(self.sindex)
        #     print(f"Número de stems únicos en el índice de stemming: {num_stems}")
        # else:
        #     print("Índice de stemming no utilizado o vacío.")

        # # dicc del permuterm
        # if self.ptindex:
        #     num_permuterms = len(self.ptindex)
        #     print(f"Número de permuterms únicos en el índice de permuterm: {num_permuterms}")
        # else:
        #     print("Índice de permuterm no utilizado o vacío.")

        # # numero total de url
        # print(f"Número de URLs únicas procesadas: {len(self.urls)}")

        # print("-" * 40)

        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################

    #################################
    ###                           ###
    ###   PARTE 2: RECUPERACION   ###
    ###                           ###
    #################################

    ###################################
    ###                             ###
    ###   PARTE 2.1: RECUPERACION   ###
    ###                             ###
    ###################################

    def solve_query(self, query: str, prev: Dict = {}):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Resuelve una query.
        Debe realizar el parsing de consulta que sera mas o menos complicado en funcion de la ampliacion que se implementen


        param:  "query": cadena con la query
                "prev": incluido por si se quiere hacer una version recursiva. No es necesario utilizarlo.


        return: posting list con el resultado de la query

        """
        # DECIDO HACER UN WHILE Y NO HACERLO RECURSIVO.



        if query is None or len(query) == 0:
            return []

        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################

        pattern = r'(\b(?:AND|OR|NOT)\b|\(|\)|\w+[-\w]*:\s*[^:\s]+|\b[\w\*\?]+\b)'
        pattern2 = r"^(?P<field>[\w-]+)\s*:\s*(?P<term>.+)$"

        tokens = re.findall(pattern, query, re.IGNORECASE)
        output_queue = []
        operator_stack = []

        for token in tokens:
            if re.match(r'\b(?:AND|OR|NOT)\b', token, re.IGNORECASE):
                while (operator_stack and operator_stack[-1] != '(' and
                       self.precedence(operator_stack[-1]) >= self.precedence(token)):
                    output_queue.append(operator_stack.pop())
                operator_stack.append(token)
            elif token == '(':
                operator_stack.append(token)
            elif token == ')':
                while operator_stack and operator_stack[-1] != '(':
                    output_queue.append(operator_stack.pop())
                operator_stack.pop()
            else:
                match = re.search(pattern2, token, re.IGNORECASE)
                if match:
                    field = match.group('field')
                    term = match.group('term').strip().lower()
                else:
                    field = 'all'
                    term = token
                output_queue.append((term.lower(), field))

        while operator_stack:
            output_queue.append(operator_stack.pop())

        return self.evaluate_postfix(output_queue)

    def precedence(self, operator):
        if operator == 'NOT':
            return 3
        elif operator in ('AND', 'OR'):
            return 2
        return 1

    def evaluate_postfix(self, tokens):
        stack = []

        for token in tokens:
            if isinstance(token, tuple):
                term, field = token
                current_posting = self.get_posting(term, field)
                stack.append(current_posting)
            else:
                if token == 'AND':
                    right = stack.pop()
                    left = stack.pop()
                    result = self.and_posting(left, right)
                elif token == 'OR':
                    right = stack.pop()
                    left = stack.pop()
                    result = self.or_posting(left, right)
                elif token == 'NOT':
                    operand = stack.pop()
                    result = self.reverse_posting(operand)
                stack.append(result)

        return stack.pop() if stack else []



    def get_posting(self, term: str, field: Optional[str] = None):
        """
        Devuelve la posting list asociada a un término.
        Dependiendo de las ampliaciones implementadas "get_posting" puede llamar a:
        - self.get_positionals: para la ampliación de posicionales
        - self.get_permuterm: para la ampliación de permuterms
        - self.get_stemming: para la ampliación de stemming

        param: "term": término del que se debe recuperar la posting list.
        "field": campo sobre el que se debe recuperar la posting list, solo necesario si se hace la ampliación de múltiples índices

        return: posting list
        NECESARIO PARA TODAS LAS VERSIONES
        """
        if re.search(r'[\*\?]', term):
            return self.get_permuterm(term, field)
        # Si el término contiene un comodín, usa el índice de permuterm
        # if '*' in term or '?' in term:
        #     return self.get_permuterm(term, field)

        # Si el stemming está activo, recupera la posting list usando el índice de stemming
        if self.use_stemming:
            return self.get_stemming(term, field)

        # Si hay un campo específico y se utilizan índices múltiples
        if field:
            if field in self.index and term in self.index[field]:
                return self.index[field][term]

        # Si no se encuentra el término, devuelve una lista vacía
        return []

    def get_positionals(self, terms: str, index):
        """

        Devuelve la posting list asociada a una secuencia de terminos consecutivos.
        NECESARIO PARA LA AMPLIACION DE POSICIONALES

        param:  "terms": lista con los terminos consecutivos para recuperar la posting list.
                "field": campo sobre el que se debe recuperar la posting list, solo necesario se se hace la ampliacion de multiples indices

        return: posting list

        """
        pass
        ########################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA DE POSICIONALES ##
        ########################################################

    def get_stemming(self, term: str, field: Optional[str] = None):
        """

        Devuelve la posting list asociada al stem de un termino.
        NECESARIO PARA LA AMPLIACION DE STEMMING

        param:  "term": termino para recuperar la posting list de su stem.
                "field": campo sobre el que se debe recuperar la posting list, solo necesario se se hace la ampliacion de multiples indices

        return: posting list

        """
        stem = self.stemmer.stem(term)
        posting_list = []

        # Si se especifica un campo y se utilizan índices múltiples
        if field and self.multifield:
            # Busca en el índice de stems del campo especificado
            if field in self.sindex and stem in self.sindex[field]:
                for term in self.sindex[field][stem]:
                    if term in self.index[field]:
                        posting_list.extend(self.index[field][term])
        else:
            # Si no se especifica campo, busca en todos los campos del índice de stems
            for fld in self.sindex:
                if stem in self.sindex[fld]:
                    for term in self.sindex[fld][stem]:
                        if term in self.index[fld]:
                            posting_list.extend(self.index[fld][term])

        return list(set(posting_list))  # Convertir a lista y eliminar duplicados
        ####################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA DE STEMMING ##
        ####################################################

    def get_permuterm(self, term: str, field: Optional[str] = None):
        """

        Devuelve la posting list asociada a un termino utilizando el indice permuterm.
        NECESARIO PARA LA AMPLIACION DE PERMUTERM

        param:  "term": termino para recuperar la posting list, "term" incluye un comodin (* o ?).
                "field": campo sobre el que se debe recuperar la posting list, solo necesario se se hace la ampliacion de multiples indices

        return: posting list

        """
        
        if '*' in term:
            split_term = term.split('*')
            # Coloca el comodín al final del término
            pbusqueda = split_term[0]
            sbusqueda = split_term[1] + '$'
            l = 0
        elif '?' in term:
            split_term = term.split('?')
            # Coloca el comodín al final del término
            pbusqueda = split_term[0]
            sbusqueda = split_term[1] + '$'
            l = len(term)

        matching_terms = []
        # Buscar en el índice permuterm correspondiente al campo especificado
        if field and field in self.ptindex:
            for permuterm, term in self.ptindex[field].items():
                pb = permuterm.startswith(pbusqueda)
                sb = permuterm.endswith(sbusqueda)
                if pb and sb:
                    if l == 0:
                        matching_terms.append(term)                            
                    elif l == len(term):
                        matching_terms.append(term)
                    
        elif field is None:
            # Si no se especifica campo, buscar en todos los campos
            for field_pt in self.ptindex.values():
                for permuterm, term in field_pt.items():
                    if permuterm.startswith(pbusqueda) and permuterm.endswith(sbusqueda) :
                        if l == 0:
                            matching_terms.append(term)                            
                        elif l == len(term):
                            matching_terms.append(term)
        else:
            return []  # Si el campo no existe en el índice, devolver lista vacía

        # Consolidar las posting lists de todos los términos encontrados
        posting_list = set()
        for term in matching_terms:
            if term in self.index[field]:
                posting_list.update(self.index[field][term])

        return list(posting_list)
        ##################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA PERMUTERM ##
        ##################################################

    def reverse_posting(self, p: list):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Devuelve una posting list con todas las noticias excepto las contenidas en p.
        Util para resolver las queries con NOT.


        param:  "p": posting list


        return: posting list con todos los artid exceptos los contenidos en p

        """

        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################
        all_art_ids = set(self.articles.keys())  # sacamos el numero de articulos
        p_set = set(p)  # pasamos a una lista
        result = list(all_art_ids - p_set)  # al ser dos conjuntos obtenemos la diferencia
        return result

    def and_posting(self, p1: list, p2: list):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Calcula el AND de dos posting list de forma EFICIENTE

        param:  "p1", "p2": posting lists sobre las que calcular


        return: posting list con los artid incluidos en p1 y p2

        """
        p1 = sorted(p1, reverse=False)
        p2 = sorted(p2, reverse=False)
        i = 0
        j = 0
        sol = []
        while i < len(p1) and j < len(p2):
            if p1[i] == p2[j]:
                sol.append(p1[i])
                i += 1
                j += 1
            elif p1[i] < p2[j]:
                i += 1
            else:
                j += 1
        return sol

        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################

    def or_posting(self, p1: list, p2: list):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Calcula el OR de dos posting list de forma EFICIENTE

        param:  "p1", "p2": posting lists sobre las que calcular


        return: posting list con los artid incluidos de p1 o p2

        """
        p1 = sorted(p1, reverse=False)
        p2 = sorted(p2, reverse=False)
        i = 0
        j = 0
        sol = []
        while i < len(p1) and j < len(p2):
            if p1[i] == p2[j]:
                sol.append(p1[i])
                i += 1
                j += 1
            elif p1[i] < p2[j]:
                sol.append(p1[i])
                i += 1
            else:
                sol.append(p2[j])
                j += 1
        while i < len(p1):  #si aun quedan elementos en p1 sigue añadiendo hasta que termina
            sol.append(p1[i])
            i += 1
        while j < len(p2):  #lo mismo pero en el caso de que pase con p2
            sol.append(p2[j])
            j += 1
        return sol
        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################

    def minus_posting(self, p1, p2):
        """
        OPCIONAL PARA TODAS LAS VERSIONES

        Calcula el except de dos posting list de forma EFICIENTE.
        Esta funcion se incluye por si es util, no es necesario utilizarla.

        param:  "p1", "p2": posting lists sobre las que calcular


        return: posting list con los artid incluidos de p1 y no en p2

        """

        pass
        ########################################################
        ## COMPLETAR PARA TODAS LAS VERSIONES SI ES NECESARIO ##
        ########################################################

    #####################################
    ###                               ###
    ### PARTE 2.2: MOSTRAR RESULTADOS ###
    ###                               ###
    #####################################

    def solve_and_count(self, ql: List[str], verbose: bool = True) -> List:
        results = []
        for query in ql:
            if len(query) > 0 and query[0] != '#':
                r = self.solve_query(query)
                results.append(len(r))
                if verbose:
                    print(f'{query}\t{len(r)}')
            else:
                results.append(0)
                if verbose:
                    print(query)
        return results

    def solve_and_test(self, ql: List[str]) -> bool:
        errors = False
        for line in ql:
            if len(line) > 0 and line[0] != '#':
                query, ref = line.split('\t')
                reference = int(ref)
                result = len(self.solve_query(query))
                if reference == result:
                    print(f'{query}\t{result}')
                else:
                    print(f'>>>>{query}\t{reference} != {result}<<<<')
                    errors = True
            else:
                print(query)
        return not errors

    def solve_and_show(self, query: str):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Resuelve una consulta y la muestra junto al numero de resultados 

        param:  "query": query que se debe resolver.

        return: el numero de artículo recuperadas, para la opcion -T

        """

        ################
        ## COMPLETAR  ##
        ################
        results = self.solve_query(query)
        num_results = len(results)

        # Muestra el número total de resultados si no es la opción -T, sino solo cuenta los resultados

        # Decide si mostrar todos los resultados o un número máximo definido
        if not self.show_all and num_results > self.SHOW_MAX:
            print(f"Showing the first {self.SHOW_MAX} results out of {num_results}:")
            display_results = results[:self.SHOW_MAX]
        else:
            print("Showing all results:")
            display_results = results
        print("=" * 40)
        # Muestra más información sobre cada resultado si está habilitado
        number = 0
        for idx in display_results:
            art_id, article = self.articles.get(idx, {})
            number += 1
            # Obtener la ruta del primer elemento de self.docs.keys()
            jsonFile = next(iter(self.docs.keys()), None)
            # obtener el numero de elementos en el archivo json
            depth = jsonFile.split('\\')[-2]
            # get number of the string
            # how to know if contains a substring
            if "/" in depth:
                depth = int(depth.split('/')[-1])
            else:
                depth= int(depth)
            docslen = len(self.docs)
            artlen = len(self.articles)
            docid = int((idx+1) % depth)

            # snippet=self.parse_article(open(jsonFile))

            digit = f"{number:02}"
            art_id = f"{art_id:02}"
            name_url = article.split('/')[-1]
            name_url = urllib.parse.unquote(name_url)
            name_url = name_url.replace('_', ' ')
            # ir al json y obtener el summary

            #hacer decode a utf-8
            name_url = name_url.encode('utf-8').decode('utf-8')
            print(f"# {digit} ({art_id}) {name_url}: {article}")
            # print(f"Snippet: {snippet}")
        print("=" * 40)
        print(f"Number of results: {num_results}")

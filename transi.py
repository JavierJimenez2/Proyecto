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

        # vamos a detectar con la ayuda de esta expresion regular cada uno de estos operadores. es la fdorma mas segura de hacerlo
        # Regex para identificar si hay un campo especificado al inicio de la consulta 
        # Identificar si hay un campo especificado al inicio de la consulta
        pattern = r'(\w+:\s*\w+|\bAND\b|\bOR\b|\bNOT\b|\w+)'
        pattern2 = r'(?P<field>\w+):(?P<term>\s*\w+)'


        tokens = re.findall(pattern, query, re.IGNORECASE)

        #nos quedamos con las posting list de todos los terminos de paso
        stack = []
        #para operadores
        stackop = []
        #para terminos
        stackterm = []
        for token in tokens:
            if token in ('AND', 'OR', 'NOT'):
                stackop.insert(0, token)
            else:
                match = re.search(pattern2, token, re.IGNORECASE)
                if match:
                    field = match.group('field')
                    term = match.group('term').strip()  # Elimina espacios en blanco alrededor del término
                else:
                    field = 'all'
                    term = token
                stackterm.insert(0,term.lower())
                current_posting = self.get_posting(term, field)
                stack.insert(0,current_posting)
        if not stackop:
            return stack[-1] if stack else []
        # pila resautlados
        result_stack = []
        current_posting = stack.pop()
        if stack:
            second_term = stack.pop()

        while stackop:
            operator = stackop.pop()
            # if stackop:
            #     if stackop[-1] == 'NOT':
            #         next_operator = stackop.pop()
            #         second_term = self.reverse_posting(second_term)
            if operator == 'AND':
                current_posting = self.and_posting(second_term, current_posting)
            elif operator == 'OR':
                current_posting = self.or_posting(second_term, current_posting)
            elif operator == 'NOT':
                current_posting = self.reverse_posting(current_posting)
            if result_stack:
                second_term = result_stack.pop()
            result_stack.append(current_posting)





        return result_stack[-1] if result_stack else []
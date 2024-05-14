class PermutermIndex:
    def __init__(self):
        self.index = {}
        self.ptindex = {}

    def add_document(self, doc_id, text):
        # Agregar el documento al índice invertido
        # Suponiendo que text es una lista de palabras
        for word in text:
            if word not in self.index:
                self.index[word] = []
            self.index[word].append(doc_id)

    def build_permuterm_index(self):
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

    def search(self, query):
        results = set()
        for field, terms in self.ptindex.items():
            for permuterm, original_term in terms.items():
                if permuterm.startswith(query):
                    results.update(self.index[field][original_term])
        return results

# Ejemplo de uso:
index = PermutermIndex()
index.add_document(1, ["apple", "banana", "orange"])
index.add_document(2, ["apple", "grape", "kiwi"])
index.build_permuterm_index()
print(index.search("an"))  # Devolverá los documentos que contienen 'banana' y 'orange'

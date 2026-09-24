import sys
import re
from typing import TextIO

# Asegura la codificación UTF-8 en la consola para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)


class Token:
    """
    Esta clase representa a un componente léxico (Token) detectado en el texto.
    Sirve como una estructura de datos para empaquetar toda la información de un lexema.
    """
    def __init__(self, tipo: str, lexema: str, linea: int):
        """
        Método constructor de la clase Token. Se ejecuta al instanciar un nuevo token.
        
        Parámetros:
        - tipo (str): La categoría gramatical/léxica (ej: 'VARIABLE', 'NUMERO').
        - lexema (str): El texto real o cadena de caracteres que fue capturada en el código.
        - linea (int): El número de línea del archivo o entrada donde se encontró el token.
        """
        self.tipo = tipo    
        self.lexema = lexema
        self.linea = linea   

    def __repr__(self):
        """
        Método especial de representación. Define cómo se transformará el objeto Token 
        a una cadena de texto (string) cuando se intente imprimir con un 'print()'.
        
        Retorna:
        - Una cadena formateada con el formato clásico de compiladores <TIPO, "lexema", línea X>.
        """
        return f'<{self.tipo}, "{self.lexema}", línea {self.linea}>'

# =========================================================================
# --- CONFIGURACIÓN DE TOKENS (EXPRESIONES REGULARES DIRECTAS) ---
# =========================================================================

# Lista explícita de palabras reservadas. Se acepta toda la palabra en mayúscula o en minúscula.
palabras_reservadas = "CARGA|carga|GUARDA|guarda|SEPARA|separa|AGREGA|agrega|RECORTA|recorta|PALANTE|palante|PATRAS|patras"

# Matriz de tuplas que define las prioridades del analizador léxico. 
# El orden importa: las expresiones de arriba se evalúan antes que las de abajo.
REGLAS_LEXICAS = [
    # 1. Constantes numéricas enteras
    ("NÚMERO",             r"\b\d+\b"),

    # 2. Archivos válidos con su extensión de 3 letras (Ej: datos.txt)
    ("NOMBRE_ARCHIVO",     r"[a-zA-Z0-9_-]+\.[a-zA-Z0-9]+"),

    # 3. Coma independiente
    ("COMA",               r","),
    
    # 4. Símbolos operativos y delimitadores del sistema
    ("SEPARADOR",          r";|=|\*|&"), 
    
    # 5. Comandos y palabras reservadas del lenguaje
    ("PALABRA_RESERVADA",  r"\b(" + palabras_reservadas + r")\b"),
    
    # 6. Formato estricto de variables (Letra minúscula inicial y largo máximo de 10)
    ("NOMBRE_VARIABLE",    r"\b[a-z][a-z0-9]{0,9}\b"),
    
    # 7. Identificadores de columnas (Inician con letra, cualquier longitud)
    ("NOMBRE_COLUMNA",     r"\b[a-zA-Z][a-zA-Z0-9]*\b"),

    # 8. Espacios
    ("ESPACIO",            r"\s+"),
    
    # 9. Captura de errores: Cualquier bloque residual que no encaja en lo anterior
    ("ERROR_LEXICO",       r"[^\s;=\*&]+"),
]

# =========================================================================
# --- CONSTRUCCIÓN DINÁMICA DEL PATRÓN REGEX ---
# =========================================================================
# Esta sección unifica todas las expresiones regulares individuales en una sola gran 
# expresión utilizando "Grupos Nombrados" (?P<Nombre>patrón) separados por el operador OR (|).
patron_lexico = "|".join(
    f"(?P<{nombre_token}>{expresion_regular})"
    for nombre_token, expresion_regular in REGLAS_LEXICAS
)
patron_lexico_compilado = re.compile(patron_lexico)


def analizar_linea(linea: str, numero_linea: int) -> list[Token]:
    """
    Función núcleo del analizador léxico encargada de procesar una cadena de texto (línea).
    
    Parámetros:
    - linea (str): El fragmento de texto a procesar.
    - numero_linea (int): El identificador de la línea actual (útil para reportar errores).

    Retorna:
    - lista_tokens (list): Una lista que contiene objetos de tipo Token ordenados conforme aparecieron.
    """
    lista_tokens = []
    
    while len(linea) != 0:
        coincidencia = patron_lexico_compilado.match(linea)
        tipo_token = coincidencia.lastgroup
        if tipo_token != 'ESPACIO':
            lexema = coincidencia.group(tipo_token)
            lista_tokens.append(Token(tipo_token, lexema, numero_linea))

        # Descartar el lexema y seguir con el resto del string
        linea = linea[coincidencia.end():]
                
    return lista_tokens

def prompt():
    print('Bari26> ', end='', flush=True)

def main(entrada: TextIO, entrada_es_stdin: bool):
    if entrada_es_stdin:
        prompt()
        
    for número, línea in enumerate(entrada):
        tokens = analizar_linea(línea, número)
        if len(tokens) == 0:
            print("[Línea vacía o sin tokens válidos]")
        else:
            for t in tokens:
                print(t)
            
        if entrada_es_stdin:
            prompt()

if __name__ == '__main__':
    # Verificar argumentos
    if len(sys.argv) > 2:
        print('Error: demasiados argumentos.')
        print(f'Uso: {sys.argv[0]} [nombre de archivo]')
        print('Sin nombre de archivo, se lee la entrada estándar.')
        sys.exit(1)
    
    # Leer un archivo si se pasó como argumento, si no leer stdin
    if len(sys.argv) == 2:
        with open(sys.argv[1], encoding='utf-8') as entrada:
            main(entrada, False)
    else:
        main(sys.stdin, True)
    
    

    


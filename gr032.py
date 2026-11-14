'''Etapa II - Analizador sintáctico
-----------------
Compiladores e Intérpretes - Cátedra Arriazu (2026)
Ingenieria en Computación (UNRN)
-----------------
Grupo N°3, Alumnos:
  Luciano Yaben
  Joaquín Rodriguez
  Enrique Nicanor Mariotti'''

import re, sys
from typing import Any, TextIO

#------------------ Etapa I: Lexi ------------------

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

# Configuración de Tokens usando REGEX directas.
# Lista explícita de palabras reservadas. 
# NOTA: Se implementa la corrección de la Etapa I, es decir, solo acepta la palabra en mayúscula.
palabras_reservadas = "CARGA|GUARDA|SEPARA|AGREGA|RECORTA|PALANTE|PATRAS"

# Lista de tuplas que define las prioridades del analizador léxico.
# Las expresiones primero en la lista se evalúan antes que las de abajo.
REGLAS_LEXICAS = [
    # 1. Constantes numéricas enteras, aquí	"\d" equivalente a [0-9]
    ("NÚMERO",             r"\b\d+\b"),

    # 2. Archivos válidos solo con extensión. Ejemplos válidos:
    #    archivo.txt
    #    archivo.json
    #    archivo.tar.gz
    #    README.md
    ("NOMBRE_ARCHIVO",     r"[a-zA-Z0-9_-]+(\.[a-zA-Z0-9]+)+"),

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

#------------------ Etapa II: Parser ------------------

# Definición de la GLC.
# sentencia                 → carga | guarda | separa | agrega | recorta | PATRAS | PALANTE
# carga                     → CARGA  argumentos_carga_o_guarda
# guarda                    → GUARDA argumentos_carga_o_guarda
# separa                    → SEPARA argumentos_separa
# agrega                    → AGREGA argumentos_agrega
# recorta                   → RECORTA argumentos_recorta
# argumentos_carga_o_guarda → nombre_archivo coma nombre_variable separador_opcional
# argumentos_separa         → nombre_variable coma nombre_variable coma columna
# argumentos_agrega         → nombre_variable coma nombre_variable
# argumentos_recorta        → nombre_variable coma numero
# separador_opcional        → coma separador | λ
# columna                   → nombre_columna | numero

class Sentencia:
    """
    Representa una sentencia sintácticamente válida.
    """
    def __init__(self, tipo: str, línea: int, argumentos: tuple[Any, ...]):
        self.tipo: str = tipo
        self.argumentos: tuple[Any, ...] = argumentos
        self.línea: int = línea

    def __str__(self) -> str:
        return f'<línea {self.línea}> {self.tipo} {self.argumentos}'

class ErrorSintáctico(Exception):
    """
    Representa un error encontrado durante el análisis sintáctico.
    """
    def __init__(self, mensaje: str, tokens_sobrantes: list[Token], línea: int = 0):
        super().__init__()
        self.mensaje: str = mensaje
        self.tokens_sobrantes: list[Token] = tokens_sobrantes
        self.línea: int = línea

    def __str__(self) -> str:
        if self.tokens_sobrantes:
            donde = f'en la línea {self.línea} cerca de "{self.tokens_sobrantes[0].lexema}"'
        else:
            donde = f'al final de la línea {self.línea}'

        return f'Error sintáctico {donde}: {self.mensaje}'

class ErrorLéxico(Exception):
    """
    Representa un error encontrado durante el análisis léxico.
    """
    def __init__(self, token_error: Token):
        super().__init__()
        self.error: Token = token_error

    def __str__(self) -> str:
        return f'Error léxico en la línea {self.error.linea}: {self.error.lexema}'

def consumir_token(tokens: list[Token], *tipos_aceptados: str) -> tuple[str, list[Token]]:
    if len(tokens) > 0 and tokens[0].tipo in tipos_aceptados:
        return tokens[0].lexema, tokens[1:]
    else:
        raise ErrorSintáctico(f'Se esperaba un token de tipo {" o ".join(tipos_aceptados)}', tokens)

def consumir_palabra_reservada(tokens: list[Token]) -> tuple[str, int, list[Token]]:
    if len(tokens) > 0 and tokens[0].tipo == 'PALABRA_RESERVADA':
        return tokens[0].lexema.upper(), tokens[0].linea, tokens[1:]
    else:
        raise ErrorSintáctico(f'Se esperaba una palabra reservada', tokens)

def consumir_separador_opcional(tokens: list[Token]) -> tuple[str|None, list[Token]]:
    if len(tokens) == 0:
        # lambda: no consume nada, si sobra algo lo detecta analizar_sintaxis()
        separador = None
    else:
        _, tokens = consumir_token(tokens, 'COMA')
        separador, tokens = consumir_token(tokens, 'SEPARADOR')
    return separador, tokens

def consumir_argumentos_carga_o_guarda(tokens: list[Token]) -> tuple[tuple[Any, ...], list[Token]]:
    nombre_archivo, tokens = consumir_token(tokens, 'NOMBRE_ARCHIVO')
    _, tokens = consumir_token(tokens, 'COMA')
    nombre_variable, tokens = consumir_token(tokens, 'NOMBRE_VARIABLE')
    separador, tokens = consumir_separador_opcional(tokens)
    argumentos = (nombre_archivo, nombre_variable, separador)
    return argumentos, tokens

def consumir_identificador_de_columna(tokens: list[Token]) -> tuple[int|str, list[Token]]:
    valor, tokens = consumir_token(tokens, 'NOMBRE_COLUMNA', 'NOMBRE_VARIABLE', 'NÚMERO')
    if valor.isdigit():
        valor = int(valor)

    return valor, tokens

def consumir_argumentos_separa(tokens: list[Token]) -> tuple[tuple[Any, ...], list[Token]]:
    nombre_variable1, tokens = consumir_token(tokens, 'NOMBRE_VARIABLE')
    _, tokens = consumir_token(tokens, 'COMA')
    nombre_variable2, tokens = consumir_token(tokens, 'NOMBRE_VARIABLE')
    _, tokens = consumir_token(tokens, 'COMA')
    columna, tokens = consumir_identificador_de_columna(tokens)
    argumentos = (nombre_variable1, nombre_variable2, columna)
    return argumentos, tokens

def consumir_argumentos_agrega(tokens: list[Token]) -> tuple[tuple[Any, ...], list[Token]]:
    nombre_variable1, tokens = consumir_token(tokens, 'NOMBRE_VARIABLE')
    _, tokens = consumir_token(tokens, 'COMA')
    nombre_variable2, tokens = consumir_token(tokens, 'NOMBRE_VARIABLE')
    argumentos = (nombre_variable1, nombre_variable2)
    return argumentos, tokens

def consumir_argumentos_recorta(tokens: list[Token]) -> tuple[tuple[Any, ...], list[Token]]:
    nombre_variable, tokens = consumir_token(tokens, 'NOMBRE_VARIABLE')
    _, tokens = consumir_token(tokens, 'COMA')
    cant_filas, tokens = consumir_token(tokens, 'NÚMERO')
    cant_filas = int(cant_filas)
    argumentos = (nombre_variable, cant_filas)
    return argumentos, tokens

def consumir_sentencia(tokens: list[Token]) -> tuple[Sentencia, list[Token]]:
    tipo_de_sentencia, línea, tokens = consumir_palabra_reservada(tokens)
    match tipo_de_sentencia:
        case 'CARGA' | 'GUARDA': argumentos, tokens = consumir_argumentos_carga_o_guarda(tokens)
        case 'SEPARA':           argumentos, tokens = consumir_argumentos_separa(tokens)
        case 'AGREGA':           argumentos, tokens = consumir_argumentos_agrega(tokens)
        case 'RECORTA':          argumentos, tokens = consumir_argumentos_recorta(tokens)
        case _:                  argumentos = ()

    sentencia = Sentencia(tipo_de_sentencia, línea, argumentos)
    return sentencia, tokens

def analizar_sintaxis(tokens: list[Token], número_línea: int) -> Sentencia|ErrorLéxico|ErrorSintáctico:
    """
    Función núcleo del analizador sintáctico encargada de procesar una lista de tokens.

    Parámetros:
    - tokens: Lista de tokens a analizar.
    - numero_linea: El identificador de la línea actual (útil para reportar errores).
    """
    errores_lexicos = [x for x in tokens if x.tipo == 'ERROR_LEXICO']
    if errores_lexicos:
        resultado = ErrorLéxico(errores_lexicos[0])
    else:
        try:
            sentencia, tokens_sobrantes = consumir_sentencia(tokens)
            if tokens_sobrantes:
                resultado = ErrorSintáctico('demasiados lexemas detectados', tokens_sobrantes, número_línea)
            else:
                resultado = sentencia
        except ErrorSintáctico as error:
            error.línea = número_línea
            resultado = error

    return resultado

def prompt():
    print('Bari26> ', end='', flush=True)

def main(entrada: TextIO, entrada_es_stdin: bool) -> int:
    if entrada_es_stdin:
        prompt()

    for número, línea in enumerate(entrada, 1):
        tokens = analizar_linea(línea, número)
        if len(tokens) != 0:
            sentencia_o_error = analizar_sintaxis(tokens, número)
            print(sentencia_o_error)

            # Si se está leyendo de un archivo, detener la ejecución al encontrar un error:
            if not entrada_es_stdin and not isinstance(sentencia_o_error, Sentencia):
                return 1

        if entrada_es_stdin:
            prompt()

    return 0

if __name__ == '__main__':

    print(__doc__)
    print("-----------------")
    print(f"Uso: {sys.argv[0]} [nombre de archivo]")
    print("Sin nombre de archivo, se lee la entrada estándar.")
    # NOTA: Se implementa la corrección de la Etapa I, es decir, se agrega una indicacion de como salir.
    print("Para detener la ejecución enviar una señal EOF (Ctrl+D en Linux o Ctrl+Z y Enter en Windows).")
    print("-----------------")

    # Verificar argumentos
    if len(sys.argv) > 2:
        print('Error: demasiados argumentos.')
        sys.exit(1)

    # Leer un archivo si se pasó como argumento, si no leer stdin
    if len(sys.argv) == 2:
        with open(sys.argv[1], encoding='utf-8') as entrada:
            exit_code = main(entrada, False)
    else:
        exit_code = main(sys.stdin, True)

    sys.exit(exit_code)

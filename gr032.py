'''Etapa II - Analizador sintáctico
-----------------
Compiladores e Intérpretes - Cátedra Arriazu (2026)
Ingenieria en Computación (UNRN)
-----------------
Grupo N°3, Alumnos:
  Luciano Yaben
  Joaquín Rodriguez
  Enrique Nicanor Mariotti'''

import sys
from typing import Any, TextIO
from gr031 import analizar_linea, Token

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
        raise ErrorSintáctico(f'Se esperaba un token de tipo {' o '.join(tipos_aceptados)}', tokens)

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

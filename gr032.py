'''Etapa II - Analizador sintáctico
-----------------
Compiladores e Intérpretres - Cátedra Arriazu (2026)
Ingenieria en Computacion (UNRN)
-----------------
Grupo N°3, Alumnos:
  Luciano Yaben
  Joaquín Rodriguez
  Enrique Nicanor Mariotti'''

import sys
from typing import TextIO
from gr031 import analizar_linea, Token

# Definición de la GLC.
# sentencia     → carga | guarda | separa | agrega | recorta | PATRAS | PALANTE
# carga         → CARGA  nombre_archivo coma nombre_variable opcional
# guarda        → GUARDA nombre_archivo coma nombre_variable opcional
# opcional      → coma separador | λ
# separa        → SEPARA nombre_variable coma nombre_variable coma columna
# columna       → nombre_columna | numero
# agrega        → AGREGA nombre_variable coma nombre_variable
# recorta       → RECORTA nombre_variable coma numero

# Funciones que representan terminales.

def tipo(tokens: list[Token], tipos: tuple[str, ...], desc: str) -> tuple[bool, list[Token], str]:
    # print(t[0].tipo in tipos) # debug
    if len(tokens) > 0 and tokens[0].tipo in tipos:
        return (True, tokens[1:], '')
    else:
        return (False, tokens, desc)

def palabra_reservada(tokens: list[Token], palabra: str) -> tuple[bool, list[Token], str]:
    if len(tokens) > 0 and tokens[0].tipo == 'PALABRA_RESERVADA' and tokens[0].lexema.upper() == palabra:
        return (True, tokens[1:], '')
    else:
        return (False, tokens, f'la palabra reservada {palabra}')

def coma(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    return tipo(tokens, ('COMA',), "una coma ','")

def nombre_variable(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    return tipo(tokens, ('NOMBRE_VARIABLE',), 'un nombre de variable')

def nombre_archivo(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    return tipo(tokens, ('NOMBRE_ARCHIVO',), 'un nombre de archivo')

def numero(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    return tipo(tokens, ('NÚMERO',), 'un número')

# nt*: Funciones que representan no terminales.

def ntOpcional(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    if len(tokens) > 0 and tokens[0].tipo == 'COMA':
        resp, tokens, esperado = tipo(tokens[1:], ('SEPARADOR',), "un separador (; = * &)")
    else:
        resp = True  # lambda: no consume nada, si sobra algo lo detecta analizar_sintaxis()
        esperado = ''
    return (resp, tokens, esperado)

def ntCarga(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    resp, tokens, esperado = palabra_reservada(tokens, 'CARGA')
    if resp: 
        resp, tokens, esperado = nombre_archivo(tokens)
    if resp: 
        resp, tokens, esperado = coma(tokens)
    if resp: 
        resp, tokens, esperado = nombre_variable(tokens)
    if resp: 
        resp, tokens, esperado = ntOpcional(tokens)
    return (resp, tokens, esperado)

def ntGuarda(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    resp, tokens, esperado = palabra_reservada(tokens, 'GUARDA')
    if resp: 
        resp, tokens, esperado = nombre_archivo(tokens)
    if resp: 
        resp, tokens, esperado = coma(tokens)
    if resp: 
        resp, tokens, esperado = nombre_variable(tokens)
    if resp: 
        resp, tokens, esperado = ntOpcional(tokens)
    return (resp, tokens, esperado)

def ntColumna(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    valores = ('NOMBRE_COLUMNA', 'NÚMERO', 'NOMBRE_VARIABLE')
    return tipo(tokens, valores, 'un nombre de columna o número de columna')

def ntSepara(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    resp, tokens, esperado = palabra_reservada(tokens, 'SEPARA')
    if resp: 
        resp, tokens, esperado = nombre_variable(tokens)
    if resp: 
        resp, tokens, esperado = coma(tokens)
    if resp: 
        resp, tokens, esperado = nombre_variable(tokens)
    if resp: 
        resp, tokens, esperado = coma(tokens)
    if resp: 
        resp, tokens, esperado = ntColumna(tokens)
    return (resp, tokens, esperado)

def ntAgrega(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    resp, tokens, esperado = palabra_reservada(tokens, 'AGREGA')
    if resp: 
        resp, tokens, esperado = nombre_variable(tokens)
    if resp: 
        resp, tokens, esperado = coma(tokens)
    if resp: 
        resp, tokens, esperado = nombre_variable(tokens)
    return (resp, tokens, esperado)

def ntRecorta(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    resp, tokens, esperado = palabra_reservada(tokens, 'RECORTA')
    if resp: 
        resp, tokens, esperado = nombre_variable(tokens)
    if resp: 
        resp, tokens, esperado = coma(tokens)
    if resp: 
        resp, tokens, esperado = numero(tokens)
    return (resp, tokens, esperado)

def ntPatras(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    return palabra_reservada(tokens, 'PATRAS')

def ntPalante(tokens: list[Token]) -> tuple[bool, list[Token], str]:
    return palabra_reservada(tokens, 'PALANTE')

def ntSentencia(tokens: list[Token]) -> tuple[bool, list[Token], str]:

    # Las palabras reservadas son terminales, pero identifican al tipo de producción.
    SENTENCIAS = {
        'CARGA': ntCarga, 'GUARDA': ntGuarda, 'SEPARA': ntSepara,
        'AGREGA': ntAgrega, 'RECORTA': ntRecorta, 'PATRAS': ntPatras,
        'PALANTE': ntPalante
    }

    # Llamada al parser de cada producción.
    if len(tokens) > 0 and tokens[0].tipo == 'PALABRA_RESERVADA':
        return SENTENCIAS[tokens[0].lexema.upper()](tokens)
    else:
        return (False, tokens, 'una palabra reservada')


def analizar_sintaxis(tokens: list[Token], numero_linea: int) -> tuple[bool, str]:
    """
    Función núcleo del analizador sintáctico encargada de procesar una lista de tokens.
    
    Parámetros:
    - tokens (list): Lista de tokens a analizar.
    - numero_linea (int): El identificador de la línea actual (útil para reportar errores).

    Retorna:
    - tuple[bool, str]: Una tupla que contiene la validez de la sentencia y un mensaje para imprimir.
    """
    errores = [x for x in tokens if x.tipo == 'ERROR_LEXICO']
    # print([token.tipo for token in tokens]) # debug
    if errores:
        ret_val = (False, f'Error léxico en línea {numero_linea}: "{errores[0].lexema}"') 
    else:
        resp, resto, esperado = ntSentencia(tokens)
        if resp:
            if len(resto) == 0:
                ret_val = (True, f'Línea {numero_linea}: sintaxis correcta')
            else:
                ret_val = (
                    False, f'Error sintáctico en línea {numero_linea}: demasiados lexemas detectados.'
                    )
        else:
            donde = f'cerca de "{resto[0].lexema}"' if resto else 'al final de la línea'
            ret_val = (
                False, f'Error sintáctico en línea {numero_linea}: {donde} se esperaba {esperado}.'
                )

    return ret_val

def prompt():
    print('Bari26> ', end='', flush=True)

def main(entrada: TextIO, entrada_es_stdin: bool):
    if entrada_es_stdin:
        prompt()

    for número, línea in enumerate(entrada, 1):
        tokens = analizar_linea(línea, número)
        if len(tokens) == 0:
            print('[Línea vacía o sin tokens válidos]')
        else:
            print(analizar_sintaxis(tokens, número)[1])

        if entrada_es_stdin:
            prompt()

if __name__ == '__main__':

    # Prints
    print(__doc__) 
    print(f"-----------------") 
    print(f"Uso: {sys.argv[0]} [nombre de archivo]")
    print(f"Sin nombre de archivo, se lee la entrada estándar.")
    print(f"-----------------") 

    # Verificar argumentos
    if len(sys.argv) > 2:
        print('Error: demasiados argumentos.')
        sys.exit(1)
    
    # Leer un archivo si se pasó como argumento, si no leer stdin
    if len(sys.argv) == 2:
        with open(sys.argv[1], encoding='utf-8') as entrada:
            main(entrada, False)
    else:
        main(sys.stdin, True)

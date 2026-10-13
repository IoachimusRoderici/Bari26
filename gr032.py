# Etapa II – Analizador sintáctico
# -----------------
# Compiladores e Intérpretres - Cátedra Arriazu (2026)
# Ingenieria en Computacion (UNRN)
# -----------------
# Alumnos:
#   Luciano Yaben
#   Joaquín Rodriguez
#   Enrique Nicanor Mariotti

import sys
from typing import TextIO
from gr031 import analizar_linea

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

def tipo(t: list, tipos: tuple, desc: str) -> tuple[bool, list, str]:
    # print(t[0].tipo in tipos) # debug
    if len(t) > 0 and t[0].tipo in tipos:
        return (True, t[1:], f'')
    return (False, t, desc)

def palabra_reservada(t: list, palabra: str) -> tuple[bool, list, str]:
    if len(t) > 0 and t[0].tipo == 'PALABRA_RESERVADA' and t[0].lexema.upper() == palabra:
        return (True, t[1:], f'')
    return (False, t, f'la palabra reservada {palabra}')

def coma(t: list) -> tuple[bool, list, str]:
    return tipo(t, ('COMA',), "una coma ','")

def nombre_variable(t: list) -> tuple[bool, list, str]:
    return tipo(t, ('NOMBRE_VARIABLE',), 'un nombre de variable')

def nombre_archivo(t: list) -> tuple[bool, list, str]:
    return tipo(t, ('NOMBRE_ARCHIVO',), 'un nombre de archivo')

def numero(t: list) -> tuple[bool, list, str]:
    return tipo(t, ('NÚMERO',), 'un número')

# nt*: Funciones que representan no terminales.

def ntOpcional(t):
    if len(t) > 0 and t[0].tipo == 'COMA':
        resp, t, esperado = tipo(t[1:], ('SEPARADOR',), "un separador (; = * &)")
    else:
        resp = True  # lambda: no consume nada, si sobra algo lo detecta analizar_sintaxis()
        esperado = f''
    return (resp, t, esperado)

def ntCarga(t: list) -> tuple[bool, list, str]:
    resp, t, esperado = palabra_reservada(t, 'CARGA')
    if resp: 
        resp, t, esperado = nombre_archivo(t)
    if resp: 
        resp, t, esperado = coma(t)
    if resp: 
        resp, t, esperado = nombre_variable(t)
    if resp: 
        resp, t, esperado = ntOpcional(t)
    return (resp, t, esperado)

def ntGuarda(t: list) -> tuple[bool, list, str]:
    resp, t, esperado = palabra_reservada(t, 'GUARDA')
    if resp: 
        resp, t, esperado = nombre_archivo(t)
    if resp: 
        resp, t, esperado = coma(t)
    if resp: 
        resp, t, esperado = nombre_variable(t)
    if resp: 
        resp, t, esperado = ntOpcional(t)
    return (resp, t, esperado)

def ntColumna(t: list) -> tuple[bool, list, str]:
    valores = ('NOMBRE_COLUMNA', 'NÚMERO', 'NOMBRE_VARIABLE')
    return tipo(t, valores, 'un nombre de columna o número de columna')

def ntSepara(t: list) -> tuple[bool, list, str]:
    resp, t, esperado = palabra_reservada(t, 'SEPARA')
    if resp: 
        resp, t, esperado = nombre_variable(t)
    if resp: 
        resp, t, esperado = coma(t)
    if resp: 
        resp, t, esperado = nombre_variable(t)
    if resp: 
        resp, t, esperado = coma(t)
    if resp: 
        resp, t, esperado = ntColumna(t)
    return (resp, t, esperado)

def ntAgrega(t: list) -> tuple[bool, list, str]:
    resp, t, esperado = palabra_reservada(t, 'AGREGA')
    if resp: 
        resp, t, esperado = nombre_variable(t)
    if resp: 
        resp, t, esperado = coma(t)
    if resp: 
        resp, t, esperado = nombre_variable(t)
    return (resp, t, esperado)

def ntRecorta(t: list) -> tuple[bool, list, str]:
    resp, t, esperado = palabra_reservada(t, 'RECORTA')
    if resp: 
        resp, t, esperado = nombre_variable(t)
    if resp: 
        resp, t, esperado = coma(t)
    if resp: 
        resp, t, esperado = numero(t)
    return (resp, t, esperado)

def ntPatras(t: list) -> tuple[bool, list, str]:
    return palabra_reservada(t, 'PATRAS')

def ntPalante(t: list) -> tuple[bool, list, str]:
    return palabra_reservada(t, 'PALANTE')

def ntSentencia(t: list) -> tuple[bool, list, str]:

    # Las palabras reservadas son terminales, pero identifican al tipo de produccion.
    SENTENCIAS = {'CARGA': ntCarga, 'GUARDA': ntGuarda, 'SEPARA': ntSepara,
                  'AGREGA': ntAgrega, 'RECORTA': ntRecorta,
                  'PATRAS': ntPatras, 'PALANTE': ntPalante}

    # Llamada al parser de cada produccion.
    if len(t) > 0 and t[0].tipo == 'PALABRA_RESERVADA':
        return SENTENCIAS[t[0].lexema.upper()](t)
    
    return (False, t, 'una palabra reservada')


def analizar_sintaxis(tokens: list, numero_linea: int) -> tuple[bool, str]:
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
                ret_val = (False, f'Error sintáctico en línea {numero_linea}: '
                                  f'demasiados lexemas detectados.')
        else:
            donde = f'cerca de "{resto[0].lexema}"' if resto else 'al final de la línea'
            ret_val = (False, f'Error sintáctico en línea {numero_linea}: {donde} '
                              f'se esperaba {esperado}.')

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
    print(f"Etapa II - Construcción del Analizador Sintáctico") 
    print(f"-----------------") 
    print(f"Compiladores e Intérpretres - Cátedra Arriazu (2026)") 
    print(f"Ingeniería en Computacion (UNRN)") 
    print(f"-----------------") 
    print(f"Grupo N°3") 
    print(f"Luciano Yaben") 
    print(f"Joaquín Rodriguez") 
    print(f"Enrique Nicanor Mariotti") 
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
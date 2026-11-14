'''Etapa III - Traducción a Código Intermedio & Programación Del Intérprete
-----------------
Compiladores e Intérpretes - Cátedra Arriazu (2026)
Ingenieria en Computación (UNRN)
-----------------
Grupo N°3, Alumnos:
  Luciano Yaben
  Joaquín Rodriguez
  Enrique Nicanor Mariotti'''

from typing import Any, TextIO
import re, sys, csv, os
import copy
import shutil

# Asegura la codificación UTF-8 en la consola para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)

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
    def __init__(self, mensaje: str, tokens_sobrantes: list[Token]):
        super().__init__()
        self.mensaje: str = mensaje
        self.tokens_sobrantes: list[Token] = tokens_sobrantes

    def __str__(self) -> str:
        if self.tokens_sobrantes:
            donde = f'cerca de "{self.tokens_sobrantes[0].lexema}"'
        else:
            donde = 'al final de la línea'

        return f'Error sintáctico {donde}: {self.mensaje}'

class ErrorLéxico(Exception):
    """
    Representa un error encontrado durante el análisis léxico.
    """
    def __init__(self, token_error: Token):
        super().__init__()
        self.error: Token = token_error

    def __str__(self) -> str:
        return f'Error léxico: {self.error.lexema}'

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

def consumir_sentencia(tokens: list[Token]) -> Sentencia:
    tipo_de_sentencia, línea, tokens = consumir_palabra_reservada(tokens)
    match tipo_de_sentencia:
        case 'CARGA' | 'GUARDA': argumentos, tokens = consumir_argumentos_carga_o_guarda(tokens)
        case 'SEPARA':           argumentos, tokens = consumir_argumentos_separa(tokens)
        case 'AGREGA':           argumentos, tokens = consumir_argumentos_agrega(tokens)
        case 'RECORTA':          argumentos, tokens = consumir_argumentos_recorta(tokens)
        case _:                  argumentos = ()

    if tokens:
        raise ErrorSintáctico('demasiados lexemas detectados', tokens)
    else:
        return Sentencia(tipo_de_sentencia, línea, argumentos)

def analizar_sintaxis(tokens: list[Token]) -> Sentencia:
    """
    Función núcleo del analizador sintáctico encargada de procesar una lista de tokens.

    Parámetros:
    - tokens: Lista de tokens a analizar.
    - numero_linea: El identificador de la línea actual (útil para reportar errores).
    """
    errores_lexicos = [x for x in tokens if x.tipo == 'ERROR_LEXICO']
    if errores_lexicos:
        raise ErrorLéxico(errores_lexicos[0])
    else:
        return consumir_sentencia(tokens)

#------------------ Etapa III: Traducción ------------------

class ErrorDeEjecución(Exception):
    """
    Representa un error encontrado durante la ejecución de una sentencia.
    """
    def __init__(self, mensaje: str, línea: int = 0):
        super().__init__()
        self.mensaje: str = mensaje

    def __str__(self) -> str:
        return f'Error de ejecución: {self.mensaje}'

class Tabla:
    def __init__(self):
        self.columnas: list[list[str]] = []

    def __str__(self) -> str:
        if not self.columnas or not self.columnas[0]:
            return "(Tabla vacía)"

        # Obtener ancho de la terminal (por defecto 80 caracteres)
        ancho_pantalla = shutil.get_terminal_size((80, 20)).columns
        ancho_celda = 15  # Ancho fijo por columna para alineación tabular

        # Preparar filas: índice 0 es encabezado, 1 en adelante son datos
        todas_las_filas = list(zip(*self.columnas))
        encabezado = todas_las_filas[0]
        datos = todas_las_filas[1:]

        # Regla de > 10 filas de datos: 5 primeras, '...', 4 últimas
        if len(datos) > 10:
            filas_a_mostrar = [encabezado] + list(datos[:5]) + [("...",) * len(encabezado)] + list(datos[-4:])
        else:
            filas_a_mostrar = [encabezado] + list(datos)

        # Calcular cuántas columnas caben por bloque en el ancho de pantalla
        cols_por_bloque = max(1, ancho_pantalla // (ancho_celda + 3))
        total_cols = len(encabezado)
        bloques_salida = []

        for inicio in range(0, total_cols, cols_por_bloque):
            fin = inicio + cols_por_bloque
            lineas_bloque = []
            for idx_fila, fila in enumerate(filas_a_mostrar):
                celdas_formateadas = []
                for celda in fila[inicio:fin]:
                    texto = str(celda)
                    if len(texto) > ancho_celda:
                        texto = texto[:ancho_celda - 2] + ".."
                    celdas_formateadas.append(f"{texto:<{ancho_celda}}")
                lineas_bloque.append(" | ".join(celdas_formateadas))
                
                # Línea separadora debajo del encabezado
                if idx_fila == 0:
                    separador = "-+-".join("-" * ancho_celda for _ in fila[inicio:fin])
                    lineas_bloque.append(separador)

            bloques_salida.append("\n".join(lineas_bloque))

        return "\n\n".join(bloques_salida)


def registrar_accion(tablas_existentes: dict[str, Tabla], acciones: dict):
    """Guarda una instantánea del estado actual antes de ejecutar una sentencia."""
    acciones["historial"].append(copy.deepcopy(tablas_existentes))
    acciones["futuro"].clear()

"""Obtiene la ruta actual .py para encontrar el archivo de datos en la misma carpeta que el script."""
def ruta_en_carpeta_script(nombre_archivo: str) -> str:
    carpeta_script = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(carpeta_script, nombre_archivo)

def ejecutar_carga(
    tablas_existentes: dict[str, Tabla], acciones: dict, nombre_archivo: str, nombre_tabla: str, separador: str|None
) -> tuple[str, Tabla|None]:
    tabla = Tabla()
    try:
        ruta_completa = ruta_en_carpeta_script(nombre_archivo)
        with open(ruta_completa, encoding="utf-8") as archivo:
            lector = csv.reader(
                archivo, delimiter=separador or ",", quotechar=None, skipinitialspace=True, strict=True
            )
            primera_fila = next(lector)
            tabla.columnas = [[nombre] for nombre in primera_fila]
            for fila in lector:
                if len(fila) != len(tabla.columnas):
                    raise ErrorDeEjecución(
                        f"El archivo {nombre_archivo} define {len(tabla.columnas)} columnas, "
                        f"pero se encontraron {len(fila)} en una fila"
                    )
                for columna, dato in zip(tabla.columnas, fila):
                    columna.append(dato)
    except ErrorDeEjecución:
        raise
    except FileNotFoundError:
        raise ErrorDeEjecución(f"No se encontró el archivo {nombre_archivo}")
    except StopIteration:
        raise ErrorDeEjecución(f"El archivo {nombre_archivo} no contiene ninguna columna")
    except Exception as error:
        raise ErrorDeEjecución(f"Error inesperado leyendo {nombre_archivo}: {type(error).__name__}, {error}")

    registrar_accion(tablas_existentes, acciones)
    tablas_existentes[nombre_tabla] = tabla
    return f"Se cargó la tabla {nombre_tabla}:", tabla


def ejecutar_guarda(
    tablas_existentes: dict[str, Tabla], acciones: dict, nombre_archivo: str, nombre_tabla: str, separador: str|None
) -> tuple[str, Tabla|None]:
    if nombre_tabla not in tablas_existentes:
        raise ErrorDeEjecución(f"No existe la tabla {nombre_tabla}")
    tabla = tablas_existentes[nombre_tabla]
    try:
        ruta_completa = ruta_en_carpeta_script(nombre_archivo)
        with open(ruta_completa, "w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(
                archivo, delimiter=separador or ",", quotechar='"', skipinitialspace=True, strict=True
            )
            escritor.writerows(zip(*tabla.columnas))
    except Exception as error:
        raise ErrorDeEjecución(f"Error inesperado escribiendo {nombre_archivo}: {type(error).__name__}, {error}")

    registrar_accion(tablas_existentes, acciones)
    return f"Se escribió la tabla {nombre_tabla} en el archivo {nombre_archivo}", tabla


def ejecutar_separa(
    tablas_existentes: dict[str, Tabla], acciones: dict, nombre_tabla1: str, nombre_tabla2: str, columna: str|int
) -> tuple[str, Tabla|None]:
    if nombre_tabla1 not in tablas_existentes:
        raise ErrorDeEjecución(f"No existe la tabla {nombre_tabla1}")
    
    tabla1 = tablas_existentes[nombre_tabla1]
    indice = -1

    # La consigna indica que la primera columna es la 1
    if isinstance(columna, int):
        if 1 <= columna <= len(tabla1.columnas):
            indice = columna - 1
        else:
            raise ErrorDeEjecución(f"Número de columna {columna} fuera de rango (1 a {len(tabla1.columnas)})")
    else:
        nombres = [col[0] for col in tabla1.columnas]
        if columna in nombres:
            indice = nombres.index(columna)
        else:
            raise ErrorDeEjecución(f"No existe la columna '{columna}' en {nombre_tabla1}")

    registrar_accion(tablas_existentes, acciones)
    
    col_extraida = tabla1.columnas.pop(indice)
    nueva_tabla = Tabla()
    nueva_tabla.columnas = [col_extraida]
    tablas_existentes[nombre_tabla2] = nueva_tabla

    return f"Se separó la columna hacia {nombre_tabla2}:", nueva_tabla


def ejecutar_agrega(
    tablas_existentes: dict[str, Tabla], acciones: dict, nombre_tabla1: str, nombre_tabla2: str
) -> tuple[str, Tabla|None]:
    # SEPARA: <nomVariable1> es la columna de ancho 1, <nomVariable2> es la tabla base
    if nombre_tabla1 not in tablas_existentes:
        raise ErrorDeEjecución(f"No existe la tabla {nombre_tabla1}")
    if nombre_tabla2 not in tablas_existentes:
        raise ErrorDeEjecución(f"No existe la tabla {nombre_tabla2}")

    t1 = tablas_existentes[nombre_tabla1]
    t2 = tablas_existentes[nombre_tabla2]

    if len(t1.columnas) != 1:
        raise ErrorDeEjecución(f"La tabla {nombre_tabla1} debe tener exactamente 1 columna")
    
    filas_base = len(t2.columnas[0])
    filas_nueva = len(t1.columnas[0])

    if filas_nueva < filas_base:
        raise ErrorDeEjecución(f"La tabla {nombre_tabla1} tiene menos filas que {nombre_tabla2}")

    registrar_accion(tablas_existentes, acciones)

    # Recorta t1 si tiene más filas que t2 y la agrega a la derecha
    columna_a_agregar = list(t1.columnas[0][:filas_base])
    t2.columnas.append(columna_a_agregar)

    return f"Se agregó {nombre_tabla1} a {nombre_tabla2}:", t2


def ejecutar_recorta(
    tablas_existentes: dict[str, Tabla], acciones: dict, nombre_tabla: str, cantidad_de_filas: int
) -> tuple[str, Tabla|None]:
    if nombre_tabla not in tablas_existentes:
        raise ErrorDeEjecución(f"No existe la tabla {nombre_tabla}")

    registrar_accion(tablas_existentes, acciones)

    tabla = tablas_existentes[nombre_tabla]
    # Sumamos 1 para mantener la fila 0 (los nombres de las columnas)
    limite = cantidad_de_filas + 1
    for i in range(len(tabla.columnas)):
        tabla.columnas[i] = tabla.columnas[i][:limite]

    return f"Se recortó {nombre_tabla} a {cantidad_de_filas} filas:", tabla


def ejecutar_patras(tablas_existentes: dict[str, Tabla], acciones: dict) -> tuple[str, Tabla|None]:
    # La consigna pide que si no hay acciones previas, no haga nada
    if not acciones["historial"]:
        return "No hay acciones anteriores para deshacer.", None

    acciones["futuro"].append(copy.deepcopy(tablas_existentes))
    estado_anterior = acciones["historial"].pop()

    tablas_existentes.clear()
    tablas_existentes.update(estado_anterior)
    return "Se deshizo la última acción (PATRAS).", None


def ejecutar_palante(tablas_existentes: dict[str, Tabla], acciones: dict) -> tuple[str, Tabla|None]:
    # La consigna pide que si no hay acciones posteriores, no haga nada
    if not acciones["futuro"]:
        return "No hay acciones posteriores para rehacer.", None

    acciones["historial"].append(copy.deepcopy(tablas_existentes))
    estado_siguiente = acciones["futuro"].pop()

    tablas_existentes.clear()
    tablas_existentes.update(estado_siguiente)
    return "Se rehizo la acción (PALANTE).", None


def ejecutar(sentencia: Sentencia, tablas_existentes: dict[str, Tabla], acciones) -> tuple[str,Tabla|None]:
    match sentencia.tipo:
        case 'CARGA':   return ejecutar_carga(tablas_existentes, acciones, *sentencia.argumentos)
        case 'GUARDA':  return ejecutar_guarda(tablas_existentes, acciones, *sentencia.argumentos)
        case 'SEPARA':  return ejecutar_separa(tablas_existentes, acciones, *sentencia.argumentos)
        case 'AGREGA':  return ejecutar_agrega(tablas_existentes, acciones, *sentencia.argumentos)
        case 'RECORTA': return ejecutar_recorta(tablas_existentes, acciones, *sentencia.argumentos)
        case 'PALANTE': return ejecutar_palante(tablas_existentes, acciones, *sentencia.argumentos)
        case 'PATRAS':  return ejecutar_patras(tablas_existentes, acciones, *sentencia.argumentos)
        case otro_tipo: raise ErrorDeEjecución(f'Tipo de sentencia inválido: {otro_tipo}')


def prompt():
    print('Bari26> ', end='', flush=True)

def main(entrada: TextIO, entrada_es_stdin: bool) -> int:
    if entrada_es_stdin:
        prompt()

    tablas_existentes: dict[str, Tabla] = {}
    acciones = acciones = {"historial": [], "futuro": []}

    for número, línea in enumerate(entrada, 1):
        tokens = analizar_linea(línea, número)
        if len(tokens) == 0:
            continue

        try:
            sentencia = analizar_sintaxis(tokens)
            mensaje, tabla_resultado = ejecutar(sentencia, tablas_existentes, acciones)
            print(mensaje)
            if tabla_resultado:
                print(tabla_resultado)
        except (ErrorLéxico, ErrorSintáctico, ErrorDeEjecución) as error:
            if entrada_es_stdin:
                print(error, file=sys.stderr)
            else:
                # Si se está leyendo de un archivo, detener la ejecución al encontrar un error
                print(f"Línea {número}:", error, file=sys.stderr)
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

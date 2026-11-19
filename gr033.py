"""
Etapa III - Traducción a Código Intermedio & Programación Del Intérprete
-----------------
Compiladores e Intérpretes - Cátedra Arriazu (2026)
Ingeniería en Computación (UNRN)
-----------------
Grupo N°3, Alumnos:
Luciano Yaben
Joaquín Rodriguez
Enrique Nicanor Mariotti
"""

from typing import Any, TextIO
import re
import sys
import csv
import os
import copy
import shutil

# Asegura la codificación UTF-8 de forma segura (compatible con Windows, Linux y Colab)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ------------------ Etapa I: Lexi ------------------

class Token:
    """
    Representa a un componente léxico (Token) detectado en el texto.
    """
    def __init__(self, tipo: str, lexema: str, linea: int):
        self.tipo = tipo
        self.lexema = lexema
        self.linea = linea

    def __repr__(self) -> str:
        return f'<{self.tipo}, "{self.lexema}", línea {self.linea}>'


palabras_reservadas = "CARGA|GUARDA|SEPARA|AGREGA|RECORTA|PALANTE|PATRAS"

REGLAS_LEXICAS = [
    ("NUMERO", r"\b\d+\b"),
    ("PALABRA_RESERVADA", r"\b(" + palabras_reservadas + r")\b"),
    ("NOMBRE_ARCHIVO", r"(?:[a-zA-Z]:[/\\]|[/\\])?[a-zA-Z0-9_.-]+(?:[/\\ ][a-zA-Z0-9_.-]+)*(\.[a-zA-Z0-9]+)+"),
    ("COMA", r","),
    ("SEPARADOR", r";|=|\*|&"),
    ("NOMBRE_VARIABLE", r"\b[a-z][a-z0-9]{0,9}\b"),
    ("NOMBRE_COLUMNA", r"\b[a-zA-Z][a-zA-Z0-9]*\b"),
    ("ESPACIO", r"\s+"),
    ("ERROR_LEXICO", r"[^\s;=\*&]+"),
]

patron_lexico = "|".join(
    f"(?P<{nombre_token}>{expresion_regular})"
    for nombre_token, expresion_regular in REGLAS_LEXICAS
)
patron_lexico_compilado = re.compile(patron_lexico)


def analizar_linea(linea: str, numero_linea: int) -> list[Token]:
    """
    Procesa una línea de texto y devuelve la lista de tokens detectados.
    """
    lista_tokens: list[Token] = []
    pos = 0
    largo = len(linea)

    while pos < largo:
        coincidencia = patron_lexico_compilado.match(linea, pos)
        if coincidencia is None:
            lista_tokens.append(Token("ERROR_LEXICO", linea[pos], numero_linea))
            pos += 1
            continue

        tipo_token = coincidencia.lastgroup
        if tipo_token and tipo_token != "ESPACIO":
            lexema = coincidencia.group(tipo_token)
            lista_tokens.append(Token(tipo_token, lexema, numero_linea))

        pos = coincidencia.end()

    return lista_tokens
# ------------------ Etapa II: Parser ------------------

class Sentencia:
    """
    Representa una sentencia sintácticamente válida.
    """
    def __init__(self, tipo: str, linea: int, argumentos: tuple[Any, ...]):
        self.tipo: str = tipo
        self.argumentos: tuple[Any, ...] = argumentos
        self.linea: int = linea

    def __str__(self) -> str:
        return f'<línea {self.linea}> {self.tipo} {self.argumentos}'


class ErrorSintactico(Exception):
    """
    Representa un error encontrado durante el análisis sintáctico.
    """
    def __init__(self, mensaje: str, tokens_sobrantes: list[Token]):
        super().__init__(mensaje)
        self.mensaje: str = mensaje
        self.tokens_sobrantes: list[Token] = tokens_sobrantes

    def __str__(self) -> str:
        if self.tokens_sobrantes:
            donde = f'cerca de "{self.tokens_sobrantes[0].lexema}"'
        else:
            donde = 'al final de la línea'
        return f'Error sintáctico {donde}: {self.mensaje}'


class ErrorLexico(Exception):
    """
    Representa un error encontrado durante el análisis léxico.
    """
    def __init__(self, token_error: Token):
        super().__init__(token_error.lexema)
        self.error: Token = token_error

    def __str__(self) -> str:
        return f'Error léxico: {self.error.lexema}'


def consumir_token(tokens: list[Token], *tipos_aceptados: str) -> tuple[str, list[Token]]:
    if len(tokens) > 0 and tokens[0].tipo in tipos_aceptados:
        return tokens[0].lexema, tokens[1:]
    raise ErrorSintactico(f'Se esperaba un token de tipo {" o ".join(tipos_aceptados)}', tokens)


def consumir_palabra_reservada(tokens: list[Token]) -> tuple[str, int, list[Token]]:
    if len(tokens) > 0 and tokens[0].tipo == 'PALABRA_RESERVADA':
        return tokens[0].lexema.upper(), tokens[0].linea, tokens[1:]
    raise ErrorSintactico('Se esperaba una palabra reservada', tokens)


def consumir_separador_opcional(tokens: list[Token]) -> tuple[str | None, list[Token]]:
    if len(tokens) == 0:
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


def consumir_identificador_de_columna(tokens: list[Token]) -> tuple[int | str, list[Token]]:
    valor, tokens = consumir_token(tokens, 'NOMBRE_COLUMNA', 'NOMBRE_VARIABLE', 'NUMERO')
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
    cant_filas, tokens = consumir_token(tokens, 'NUMERO')
    cant_filas_int = int(cant_filas)
    argumentos = (nombre_variable, cant_filas_int)
    return argumentos, tokens


def consumir_sentencia(tokens: list[Token]) -> Sentencia:
    tipo_de_sentencia, linea, tokens = consumir_palabra_reservada(tokens)
    match tipo_de_sentencia:
        case 'CARGA' | 'GUARDA':
            argumentos, tokens = consumir_argumentos_carga_o_guarda(tokens)
        case 'SEPARA':
            argumentos, tokens = consumir_argumentos_separa(tokens)
        case 'AGREGA':
            argumentos, tokens = consumir_argumentos_agrega(tokens)
        case 'RECORTA':
            argumentos, tokens = consumir_argumentos_recorta(tokens)
        case 'PALANTE' | 'PATRAS':
            argumentos = ()
        case _:
            argumentos = ()

    if tokens:
        raise ErrorSintactico('demasiados lexemas detectados', tokens)

    return Sentencia(tipo_de_sentencia, linea, argumentos)


def analizar_sintaxis(tokens: list[Token]) -> Sentencia:
    """
    Procesa una lista de tokens y devuelve una Sentencia válida.
    """
    errores_lexicos = [x for x in tokens if x.tipo == 'ERROR_LEXICO']
    if errores_lexicos:
        raise ErrorLexico(errores_lexicos[0])
    return consumir_sentencia(tokens)
# ------------------ Etapa III: Traducción e Intérprete ------------------

class ErrorDeEjecucion(Exception):
    """
    Representa un error semántico o de ejecución durante la interpretación.
    """
    def __init__(self, mensaje: str, linea: int = 0):
        super().__init__(mensaje)
        self.mensaje: str = mensaje
        self.linea: int = linea

    def __str__(self) -> str:
        return f'Error de ejecución: {self.mensaje}'


class Tabla:
    def __init__(self):
        self.columnas: list[list[str]] = []

    def __str__(self) -> str:
        if not self.columnas or not self.columnas[0]:
            return "(Tabla vacía)"

        ancho_pantalla = shutil.get_terminal_size((80, 20)).columns
        ancho_celda = 15

        todas_las_filas = list(zip(*self.columnas))
        encabezado = todas_las_filas[0]
        datos = todas_las_filas[1:]

        if len(datos) > 10:
            filas_a_mostrar = (
                [encabezado]
                + list(datos[:5])
                + [("...",) * len(encabezado)]
                + list(datos[-4:])
            )
        else:
            filas_a_mostrar = [encabezado] + list(datos)

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

                if idx_fila == 0:
                    separador = "-+-".join("-" * ancho_celda for _ in fila[inicio:fin])
                    lineas_bloque.append(separador)

            bloques_salida.append("\n".join(lineas_bloque))

        return "\n\n".join(bloques_salida)


def registrar_accion(tablas_existentes: dict[str, Tabla], acciones: dict[str, list[Any]]) -> None:
    """Guarda una instantánea del estado actual antes de modificar las tablas."""
    acciones["historial"].append(copy.deepcopy(tablas_existentes))
    acciones["futuro"].clear()


def ruta_en_carpeta_script(nombre_archivo: str) -> str:
    """
    Resuelve la ruta del archivo de datos tanto si se ejecuta como .py local
    como si se ejecuta en Google Colab o consola interactiva (donde __file__ no existe).
    """
    if os.path.isabs(nombre_archivo) or os.path.exists(nombre_archivo):
        return nombre_archivo
    try:
        carpeta_script = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(carpeta_script, nombre_archivo)
    except NameError:
        return os.path.join(os.getcwd(), nombre_archivo)


def ejecutar_carga(
    tablas_existentes: dict[str, Tabla],
    acciones: dict[str, list[Any]],
    nombre_archivo: str,
    nombre_tabla: str,
    separador: str | None,
) -> tuple[str, Tabla | None]:
    tabla = Tabla()
    try:
        ruta_completa = ruta_en_carpeta_script(nombre_archivo)
        with open(ruta_completa, encoding="utf-8", newline="") as archivo:
            lector = csv.reader(
                archivo,
                delimiter=separador or ",",
                quotechar='"',
                skipinitialspace=True,
                strict=True,
            )
            primera_fila = next(lector)
            if not primera_fila:
                raise ErrorDeEjecucion(f"El archivo {nombre_archivo} está vacío")

            tabla.columnas = [[nombre] for nombre in primera_fila]
            for fila in lector:
                if not fila:
                    continue
                if len(fila) != len(tabla.columnas):
                    raise ErrorDeEjecucion(
                        f"El archivo {nombre_archivo} define {len(tabla.columnas)} columnas, "
                        f"pero se encontraron {len(fila)} en una fila"
                    )
                for columna, dato in zip(tabla.columnas, fila):
                    columna.append(dato)

    except ErrorDeEjecucion:
        raise
    except FileNotFoundError:
        raise ErrorDeEjecucion(f"No se encontró el archivo {nombre_archivo}")
    except StopIteration:
        raise ErrorDeEjecucion(f"El archivo {nombre_archivo} no contiene ninguna columna")
    except Exception as error:
        raise ErrorDeEjecucion(f"Error inesperado leyendo {nombre_archivo}: {type(error).__name__}, {error}")

    registrar_accion(tablas_existentes, acciones)
    tablas_existentes[nombre_tabla] = tabla
    return f"Se cargó la tabla {nombre_tabla}:", tabla


def ejecutar_guarda(
    tablas_existentes: dict[str, Tabla],
    acciones: dict[str, list[Any]],
    nombre_archivo: str,
    nombre_tabla: str,
    separador: str | None,
) -> tuple[str, Tabla | None]:
    if nombre_tabla not in tablas_existentes:
        raise ErrorDeEjecucion(f"No existe la tabla {nombre_tabla}")

    tabla = tablas_existentes[nombre_tabla]
    try:
        ruta_completa = ruta_en_carpeta_script(nombre_archivo)
        with open(ruta_completa, "w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(
                archivo,
                delimiter=separador or ",",
                quotechar='"',
                skipinitialspace=True,
                strict=True,
            )
            if tabla.columnas:
                escritor.writerows(zip(*tabla.columnas))
    except Exception as error:
        raise ErrorDeEjecucion(f"Error inesperado escribiendo {nombre_archivo}: {type(error).__name__}, {error}")

    return f"Se escribió la tabla {nombre_tabla} en el archivo {nombre_archivo}", None


def ejecutar_separa(
    tablas_existentes: dict[str, Tabla],
    acciones: dict[str, list[Any]],
    nombre_tabla1: str,
    nombre_tabla2: str,
    columna: str | int,
) -> tuple[str, Tabla | None]:
    if nombre_tabla1 not in tablas_existentes:
        raise ErrorDeEjecucion(f"No existe la tabla {nombre_tabla1}")

    tabla1 = tablas_existentes[nombre_tabla1]
    if not tabla1.columnas:
        raise ErrorDeEjecucion(f"La tabla {nombre_tabla1} no tiene columnas para separar")

    indice = -1
    if isinstance(columna, int):
        if 1 <= columna <= len(tabla1.columnas):
            indice = columna - 1
        else:
            raise ErrorDeEjecucion(f"Número de columna {columna} fuera de rango (1 a {len(tabla1.columnas)})")
    else:
        nombres = [col[0] for col in tabla1.columnas]
        if columna in nombres:
            indice = nombres.index(columna)
        else:
            raise ErrorDeEjecucion(f"No existe la columna '{columna}' en {nombre_tabla1}")

    registrar_accion(tablas_existentes, acciones)
    col_extraida = tabla1.columnas.pop(indice)
    nueva_tabla = Tabla()
    nueva_tabla.columnas = [col_extraida]
    tablas_existentes[nombre_tabla2] = nueva_tabla
    return f"Se separó la columna hacia {nombre_tabla2}:", nueva_tabla
def ejecutar_agrega(
    tablas_existentes: dict[str, Tabla],
    acciones: dict[str, list[Any]],
    nombre_tabla1: str,
    nombre_tabla2: str,
) -> tuple[str, Tabla | None]:
    if nombre_tabla1 not in tablas_existentes:
        raise ErrorDeEjecucion(f"No existe la tabla {nombre_tabla1}")
    if nombre_tabla2 not in tablas_existentes:
        raise ErrorDeEjecucion(f"No existe la tabla {nombre_tabla2}")

    t1 = tablas_existentes[nombre_tabla1]
    t2 = tablas_existentes[nombre_tabla2]

    if len(t1.columnas) != 1:
        raise ErrorDeEjecucion(f"La tabla {nombre_tabla1} debe tener exactamente 1 columna")
    if not t2.columnas:
        raise ErrorDeEjecucion(f"La tabla {nombre_tabla2} no tiene columnas base")

    filas_base = len(t2.columnas[0])
    filas_nueva = len(t1.columnas[0])
    if filas_nueva < filas_base:
        raise ErrorDeEjecucion(f"La tabla {nombre_tabla1} tiene menos filas que {nombre_tabla2}")

    registrar_accion(tablas_existentes, acciones)
    columna_a_agregar = list(t1.columnas[0][:filas_base])
    t2.columnas.append(columna_a_agregar)
    return f"Se agregó {nombre_tabla1} a {nombre_tabla2}:", t2


def ejecutar_recorta(
    tablas_existentes: dict[str, Tabla],
    acciones: dict[str, list[Any]],
    nombre_tabla: str,
    cantidad_de_filas: int,
) -> tuple[str, Tabla | None]:
    if nombre_tabla not in tablas_existentes:
        raise ErrorDeEjecucion(f"No existe la tabla {nombre_tabla}")

    tabla = tablas_existentes[nombre_tabla]
    if not tabla.columnas:
        raise ErrorDeEjecucion(f"La tabla {nombre_tabla} está vacía")

    registrar_accion(tablas_existentes, acciones)
    limite = cantidad_de_filas + 1
    for i in range(len(tabla.columnas)):
        tabla.columnas[i] = tabla.columnas[i][:limite]

    return f"Se recortó {nombre_tabla} a {cantidad_de_filas} filas:", tabla


def ejecutar_patras(
    tablas_existentes: dict[str, Tabla],
    acciones: dict[str, list[Any]],
) -> tuple[str, Tabla | None]:
    if not acciones["historial"]:
        return "No hay acciones anteriores para deshacer.", None

    acciones["futuro"].append(copy.deepcopy(tablas_existentes))
    estado_anterior = acciones["historial"].pop()
    tablas_existentes.clear()
    tablas_existentes.update(estado_anterior)
    return "Se deshizo la última acción (PATRAS).", None


def ejecutar_palante(
    tablas_existentes: dict[str, Tabla],
    acciones: dict[str, list[Any]],
) -> tuple[str, Tabla | None]:
    if not acciones["futuro"]:
        return "No hay acciones posteriores para rehacer.", None

    acciones["historial"].append(copy.deepcopy(tablas_existentes))
    estado_siguiente = acciones["futuro"].pop()
    tablas_existentes.clear()
    tablas_existentes.update(estado_siguiente)
    return "Se rehizo la acción (PALANTE).", None


def ejecutar(
    sentencia: Sentencia,
    tablas_existentes: dict[str, Tabla],
    acciones: dict[str, list[Any]],
) -> tuple[str, Tabla | None]:
    match sentencia.tipo:
        case 'CARGA':
            return ejecutar_carga(tablas_existentes, acciones, *sentencia.argumentos)
        case 'GUARDA':
            return ejecutar_guarda(tablas_existentes, acciones, *sentencia.argumentos)
        case 'SEPARA':
            return ejecutar_separa(tablas_existentes, acciones, *sentencia.argumentos)
        case 'AGREGA':
            return ejecutar_agrega(tablas_existentes, acciones, *sentencia.argumentos)
        case 'RECORTA':
            return ejecutar_recorta(tablas_existentes, acciones, *sentencia.argumentos)
        case 'PALANTE':
            return ejecutar_palante(tablas_existentes, acciones)
        case 'PATRAS':
            return ejecutar_patras(tablas_existentes, acciones)
        case otro_tipo:
            raise ErrorDeEjecucion(f'Tipo de sentencia inválido: {otro_tipo}')


def prompt() -> None:
    print('Bari26> ', end='', flush=True)


def main(entrada: TextIO, entrada_es_stdin: bool) -> int:
    if entrada_es_stdin:
        prompt()

    tablas_existentes: dict[str, Tabla] = {}
    acciones: dict[str, list[Any]] = {"historial": [], "futuro": []}

    for numero, linea in enumerate(entrada, 1):
        try:
            tokens = analizar_linea(linea, numero)
            if len(tokens) > 0:
                sentencia = analizar_sintaxis(tokens)
                mensaje, tabla_resultado = ejecutar(sentencia, tablas_existentes, acciones)
                print(mensaje)
                if tabla_resultado:
                    print(tabla_resultado)
        except (ErrorLexico, ErrorSintactico, ErrorDeEjecucion) as error:
            if entrada_es_stdin:
                print(error, file=sys.stderr)
            else:
                print(f"Línea {numero}:", error, file=sys.stderr)
                return 1

        if entrada_es_stdin:
            prompt()

    return 0


if __name__ == '__main__':
    print(__doc__)
    print("-----------------")
    print(f"Uso: {sys.argv[0]} [nombre de archivo]")
    print("Sin nombre de archivo, se lee la entrada estándar.")
    print("Para detener la ejecución enviar una señal EOF (Ctrl+D en Linux o Ctrl+Z y Enter en Windows).")
    print("-----------------")

    if len(sys.argv) > 2:
        print('Error: demasiados argumentos.')
        sys.exit(1)

    if len(sys.argv) == 2:
        with open(sys.argv[1], encoding='utf-8') as archivo_entrada:
            exit_code = main(archivo_entrada, False)
    else:
        exit_code = main(sys.stdin, True)

    sys.exit(exit_code)

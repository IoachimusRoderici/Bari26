import sys
import re
from typing import TextIO

# Asegura la codificación UTF-8 en la consola para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)

# --- CLASE TOKEN PARA ESTRUCTURAR EL ANÁLISIS ---
class Token:
    """
    Esta clase representa a un componente léxico (Token) detectado en el texto.
    Sirve como una estructura de datos para empaquetar toda la información de un lexema.
    """
    def __init__(self, tipo, lexema, linea, estado=""):
        """
        Método constructor de la clase Token. Se ejecuta al instanciar un nuevo token.
        
        Parámetros:
        - tipo (str): La categoría gramatical/léxica (ej: 'VARIABLE', 'NUMERO').
        - lexema (str): El texto real o cadena de caracteres que fue capturada en el código.
        - linea (int): El número de línea del archivo o entrada donde se encontró el token.
        - estado (str): Información adicional opcional (ej: 'Válida', 'No cumple formato').
        """
        self.tipo = tipo        
        self.lexema = lexema    
        self.linea = linea      
        self.estado = estado    

    def __repr__(self):
        """
        Método especial de representación. Define cómo se transformará el objeto Token 
        a una cadena de texto (string) cuando se intente imprimir con un 'print()'.
        
        Retorna:
        - Una cadena formateada con el formato clásico de compiladores <TIPO, "lexema", línea X>.
        """
        # Si el token incluye un estado especial, se formatea de manera extendida
        if self.estado != "":
            texto = "<" + self.tipo + " (" + self.estado + '), "' + self.lexema + '", línea ' + str(self.linea) + ">"
            return texto
        # Formato estándar para tokens comunes sin estados adicionales
        texto = "<" + self.tipo + ', "' + self.lexema + '", línea ' + str(self.linea) + ">"
        return texto

# =========================================================================
# --- CONFIGURACIÓN DE TOKENS (EXPRESIONES REGULARES DIRECTAS) ---
# =========================================================================

# Lista explícita de palabras reservadas. Se acepta toda la palabra en mayúscula o en minúscula.
patron_palabras = "CARGA|carga|GUARDA|guarda|SEPARA|separa|AGREGA|agrega|RECORTA|recorta|PALANTE|palante|PATRAS|patras"

# Matriz de tuplas que define las prioridades del analizador léxico. 
# El orden importa: las expresiones de arriba se evalúan antes que las de abajo.
REGLAS_LEXICAS = [
    # 1. Coordenadas de dimensión o cuadrícula (Ej: 52,36 o 20,53). Máxima prioridad.
    ("COLUMNAS_FILAS",     r"\d+,\d+"),

    # 2. Archivos válidos con su extensión de 3 letras (Ej: datos.txt)
    ("NOMBRE_ARCHIVO",     r"[a-zA-Z0-9_-]+\.[a-zA-Z]{3}"),

    # 3. Coma independiente (solo se activa si no forma parte de COLUMNAS_FILAS)
    ("COMA",               r","),
    
    # 4. Símbolos operativos y delimitadores del sistema
    ("SEPARADOR",          r";|=|\*|&"), 
    
    # 5. Comandos y palabras reservadas del lenguaje
    ("PALABRA_RESERVADA",  r"\b(" + patron_palabras + r")\b"),
    
    # 6. Formato estricto de variables (Letra minúscula inicial y largo máximo de 10)
    ("VARIABLE",           r"\b[a-z][a-z0-9]{0,9}\b"),
    
    # 7. Identificadores de columnas (Inician con letra, cualquier longitud)
    ("NOMBRE_COLUMNA",     r"\b[a-zA-Z][a-zA-Z0-9]*\b"),
    
    # 8. Constantes numéricas enteras sueltas (Ej: números que no están junto a una coma)
    ("NUMERO",             r"\b\d+\b"),
    
    # 9. Captura de errores: Cualquier bloque residual que no encajó en lo anterior
    ("ERROR_LEXICO",       r"[^\s,;=*&.]+")
]

# =========================================================================
# --- CONSTRUCCIÓN DINÁMICA DEL PATRÓN REGEX ---
# =========================================================================
# Esta sección unifica todas las expresiones regulares individuales en una sola gran 
# expresión utilizando "Grupos Nombrados" (?P<Nombre>patrón) separados por el operador OR (|).
partes_del_patron = []
for nombre_token, expresion_regular in REGLAS_LEXICAS:
    # Se etiqueta cada sub-patrón con el nombre de su token correspondiente
    bloque = "(?P<" + nombre_token + ">" + expresion_regular + ")"
    partes_del_patron.append(bloque)

# Se unen todos los bloques con el carácter '|' (OR lógico de expresiones regulares)
patron_lexico = "|".join(partes_del_patron)


def analizar_linea(linea, numero_linea):
    """
    Función núcleo del analizador léxico encargada de procesar una cadena de texto (línea).
    
    ¿Cómo funciona?
    Utiliza un iterador de expresiones regulares (`re.finditer`) que barre la línea de izquierda 
    a derecha. Cada vez que encuentra un fragmento que coincide con el patrón global, identifica 
    cuál de los grupos nombrados fue el que reaccionó (`coincidencia.lastgroup`). Luego, crea un 
    objeto de la clase `Token` y lo almacena.

    Parámetros:
    - linea (str): El fragmento de texto a procesar.
    - numero_linea (int): El identificador de la línea actual (útil para reportar errores).

    Retorna:
    - lista_tokens (list): Una lista que contiene objetos de tipo Token ordenados conforme aparecieron.
    """
    lista_tokens = []
    
    # re.finditer busca todas las coincidencias que no se superpongan en la línea de texto
    for coincidencia in re.finditer(patron_lexico, linea):
        
        # Recupera el nombre del grupo regex que coincidió (ej: "VARIABLE" o "NUMERO")
        tipo_token_detectado = coincidencia.lastgroup
        # Extrae el texto real que activó esa coincidencia específica
        lexema_detectado = coincidencia.group(tipo_token_detectado)
        
        # Estructura condicional (if/elifs) para procesar el token según su tipo clasificado
        if tipo_token_detectado == "COLUMNAS_FILAS":
            nuevo_token = Token("COLUMNAS_FILAS", lexema_detectado, numero_linea)
            lista_tokens.append(nuevo_token)
            
        elif tipo_token_detectado == "NOMBRE_ARCHIVO":
            nuevo_token = Token("NOMBRE_ARCHIVO", lexema_detectado, numero_linea)
            lista_tokens.append(nuevo_token)
            
        elif tipo_token_detectado == "COMA":
            nuevo_token = Token("COMA", lexema_detectado, numero_linea)
            lista_tokens.append(nuevo_token)
            
        elif tipo_token_detectado == "SEPARADOR":
            nuevo_token = Token("SEPARADOR", lexema_detectado, numero_linea)
            lista_tokens.append(nuevo_token)
            
        elif tipo_token_detectado == "PALABRA_RESERVADA":
            nuevo_token = Token("PALABRA_RESERVADA", lexema_detectado, numero_linea)
            lista_tokens.append(nuevo_token)
            
        elif tipo_token_detectado == "VARIABLE":
            # Las variables añaden de manera fija el estado "Válida" para confirmar su sintaxis
            nuevo_token = Token("VARIABLE", lexema_detectado, numero_linea, "Válida")
            lista_tokens.append(nuevo_token)
            
        elif tipo_token_detectado == "NOMBRE_COLUMNA":
            nuevo_token = Token("NOMBRE_COLUMNA", lexema_detectado, numero_linea)
            lista_tokens.append(nuevo_token)
            
        elif tipo_token_detectado == "NUMERO":
            nuevo_token = Token("NUMERO", lexema_detectado, numero_linea)
            lista_tokens.append(nuevo_token)
            
        elif tipo_token_detectado == "ERROR_LEXICO":
            # Cualquier texto que no encajó se clasifica con el estado "No cumple formato"
            nuevo_token = Token("ERROR_LEXICO", lexema_detectado, numero_linea, "No cumple formato")
            lista_tokens.append(nuevo_token)
                
    return lista_tokens

def prompt():
    print('Bari26> ', end='', flush=True)

if __name__ == '__main__':
    # Verificar argumentos
    if len(sys.argv) > 2:
        print('Error: demasiados argumentos.')
        print(f'Uso: {sys.argv[0]} [nombre de archivo]')
        print('Sin nombre de archivo, se lee la entrada estándar.')
        sys.exit(1)
    
    # Leer un archivo si se pasó como argumento, si no leer stdin
    entrada: TextIO
    imprimir_prompt: bool
    if len(sys.argv) == 2:
        entrada = open(sys.argv[1])
        imprimir_prompt = False
    else:
        entrada = sys.stdin
        imprimir_prompt = True
    
    if imprimir_prompt:
        prompt()

    for número, línea in enumerate(entrada):
        tokens = analizar_linea(línea, número)
        if len(tokens) == 0:
            print("[Línea vacía o sin tokens válidos]")
        else:
            for t in tokens:
                print(t)
            
        if imprimir_prompt:
            prompt()

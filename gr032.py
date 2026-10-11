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
import re
from typing import TextIO
import gr031 as lexi

# Definición de la GLC.
# sentencia     → carga | guarda | separa | agrega | recorta | PATRAS | PALANTE
# carga         → CARGA  nombre_archivo ',' nombre_variable opcional
# guarda        → GUARDA nombre_archivo ',' nombre_variable opcional
# opcional      → ',' separador | λ
# separa        → SEPARA nombre_variable ',' nombre_variable ',' columna
# columna       → ',' nombre_columna | numero
# agrega        → AGREGA nombre_variable ',' nombre_variable
# recorta       → RECORTA nombre_variable ',' numero

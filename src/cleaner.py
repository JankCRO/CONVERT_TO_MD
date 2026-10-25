import re

# Expresiones regulares precompiladas para optimizar el rendimiento
RE_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufeff]")
RE_PAGE_FRACTION = re.compile(
    r"^\s*(?:p[áa]gina|page|p[áa]g\.?)\s+\d+\s*(?:de|of|/)\s*\d+\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
RE_ISOLATED_PAGE_NUM = re.compile(
    r"(?:^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$)",
    flags=re.MULTILINE,
)
RE_MULTI_SPACE = re.compile(r"[ \t]{2,}")
RE_MULTI_NEWLINE = re.compile(r"\n{3,}")


def _limpiar_bloque_texto(bloque: str) -> str:
    """Limpia un segmento de texto fuera de bloques de código."""
    # Eliminar numeración tipo "Página X de Y" o "Page X of Y"
    bloque = RE_PAGE_FRACTION.sub("", bloque)

    # Eliminar números de página aislados en su propia línea
    bloque = RE_ISOLATED_PAGE_NUM.sub("", bloque)

    # Limpiar espacios al final de cada línea preservando la indentación de listas Markdown
    lineas_procesadas: list[str] = []
    for linea in bloque.splitlines():
        linea_sin_cola = linea.rstrip()
        if not linea_sin_cola.strip():
            lineas_procesadas.append("")
            continue

        # Preservar indentación inicial (útil para listas anidadas), normalizando espacios internos dobles
        match_indent = re.match(r"^(\s*)(.*)$", linea_sin_cola)
        if match_indent:
            indent, contenido = match_indent.groups()
            contenido = RE_MULTI_SPACE.sub(" ", contenido)
            lineas_procesadas.append(f"{indent}{contenido}")
        else:
            lineas_procesadas.append(linea_sin_cola)

    return "\n".join(lineas_procesadas)


def limpiar_texto(texto: str) -> str:
    """
    Elimina ruido de formato, pies de página y saltos de línea redundantes
    preservando bloques de código, tablas e indentación válida de Markdown.

    Args:
        texto: Contenido bruto extraído por el motor de conversión.

    Returns:
        Texto en formato Markdown limpio y optimizado para ventana de contexto de LLMs.
    """
    if not texto or not texto.strip():
        return ""

    # 1. Normalizar saltos de línea (CRLF/CR -> LF) y saltos de página (\f -> \n\n)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n")

    # 2. Eliminar caracteres de control invisibles o BOM residuales
    texto = RE_CONTROL_CHARS.sub("", texto)

    # 3. Separar bloques de código cercados (```...```) para no alterar su contenido ni indentación
    partes = re.split(r"(```[\s\S]*?```)", texto)
    partes_limpias: list[str] = []

    for indice, parte in enumerate(partes):
        if indice % 2 == 1:
            # Es un bloque de código cercado: solo limpiamos espacios en cola por línea
            lineas_codigo = [l.rstrip() for l in parte.splitlines()]
            partes_limpias.append("\n".join(lineas_codigo))
        else:
            partes_limpias.append(_limpiar_bloque_texto(parte))

    resultado = "".join(partes_limpias)

    # 4. Colapsar 3 o más saltos de línea consecutivos en máximo 2 (un párrafo en blanco)
    resultado = RE_MULTI_NEWLINE.sub("\n\n", resultado)

    return resultado.strip() + "\n"

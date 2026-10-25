from datetime import datetime
from pathlib import Path
from typing import Optional
import yaml


def estimar_tokens(texto: str) -> int:
    """
    Realiza una estimación heurística de tokens (~4 caracteres por token en promedio)
    para orientar el uso en ventanas de contexto de LLMs.
    """
    if not texto:
        return 0
    return max(1, round(len(texto) / 4))


def generar_frontmatter(ruta_archivo: str | Path, texto_limpio: Optional[str] = None) -> str:
    """
    Genera un bloque YAML Frontmatter estandarizado con metadatos del documento procesado.

    Args:
        ruta_archivo: Ruta al archivo original de entrada.
        texto_limpio: Texto ya procesado (opcional) para incluir métricas de longitud/tokens.

    Returns:
        Cadena con el bloque YAML delimitado por `---` listo para encabezar el archivo Markdown.

    Raises:
        FileNotFoundError: Si el archivo de origen no existe.
    """
    ruta = Path(ruta_archivo).resolve()
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de origen: {ruta}")

    estadisticas = ruta.stat()
    datos: dict[str, str | int | float] = {
        "archivo_origen": ruta.name,
        "formato_origen": ruta.suffix.lower().lstrip(".") or "desconocido",
        "fecha_procesamiento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tamano_origen_kb": round(estadisticas.st_size / 1024, 2),
    }

    if texto_limpio is not None:
        datos["caracteres_md"] = len(texto_limpio)
        datos["tokens_estimados"] = estimar_tokens(texto_limpio)

    datos["procesado_por"] = "CONVERT_TO_MD"

    frontmatter = yaml.safe_dump(
        datos,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()

    return f"---\n{frontmatter}\n---\n\n"

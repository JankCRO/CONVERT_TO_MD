import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk
from markitdown import MarkItDown

from .cleaner import limpiar_texto
from .metadata import estimar_tokens, generar_frontmatter

# Integración con fallback seguro de TkinterDnD2 para soporte Drag & Drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    class BaseWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        """Ventana base CTk con soporte nativo para eventos Drag & Drop."""

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)

    CAN_USE_DND = True
except Exception:
    BaseWindow = ctk.CTk  # type: ignore[misc,assignment]
    DND_FILES = "DND_Files"
    CAN_USE_DND = False


EXTENSIONES_PERMITIDAS: set[str] = {".pdf", ".docx", ".html", ".htm", ".txt"}


def obtener_directorio_base() -> Path:
    """
    Obtiene el directorio raíz de ejecución compatible tanto con desarrollo local
    como con binarios empaquetados mediante PyInstaller (`sys.frozen`).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


class ConvertToMDApp(BaseWindow):
    """Aplicación principal de escritorio CONVERT_TO_MD."""

    # Paleta de colores adaptativa (Modo Claro, Modo Oscuro)
    COLOR_BG = ("#F8FAFC", "#0F172A")
    COLOR_CARD = ("#FFFFFF", "#1E293B")
    COLOR_DROPZONE = ("#F1F5F9", "#172033")
    COLOR_DROPZONE_BORDER = ("#CBD5E1", "#334155")
    COLOR_PRIMARY = ("#2563EB", "#3B82F6")
    COLOR_PRIMARY_HOVER = ("#1D4ED8", "#2563EB")
    COLOR_SECONDARY = ("#E2E8F0", "#334155")
    COLOR_SECONDARY_HOVER = ("#CBD5E1", "#475569")
    COLOR_TEXT_MAIN = ("#0F172A", "#F8FAFC")
    COLOR_TEXT_MUTED = ("#64748B", "#94A3B8")

    # Colores de estado
    STATUS_IDLE = ("#64748B", "#94A3B8")
    STATUS_LOADING = ("#2563EB", "#60A5FA")
    STATUS_SUCCESS = ("#059669", "#34D399")
    STATUS_ERROR = ("#DC2626", "#F87171")

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("CONVERT_TO_MD — Optimizador de Documentos para LLMs")
        self.geometry("780x640")
        self.minsize(680, 560)
        self.configure(fg_color=self.COLOR_BG)

        # Estado interno
        self._converter: Optional[MarkItDown] = None
        self._procesando: bool = False
        self._ultimo_markdown: str = ""
        self.directorio_salida: Path = obtener_directorio_base() / "output"

        self._construir_interfaz()
        self._configurar_drag_and_drop()

    def _construir_interfaz(self) -> None:
        """Construye y distribuye todos los componentes visuales de la ventana."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Barra superior (Encabezado y Selector de Tema)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        title_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_container.grid(row=0, column=0, sticky="w")

        self.title_label = ctk.CTkLabel(
            title_container,
            text="CONVERT_TO_MD",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=self.COLOR_TEXT_MAIN,
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            title_container,
            text="Conversión local a Markdown limpio con YAML Frontmatter para contextos de LLMs",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
        )
        self.subtitle_label.pack(anchor="w", pady=(2, 0))

        self.theme_selector = ctk.CTkSegmentedButton(
            self.header_frame,
            values=["Sistema", "Claro", "Oscuro"],
            command=self._cambiar_tema,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.theme_selector.set("Sistema")
        self.theme_selector.grid(row=0, column=1, sticky="e")

        # 2. Zona de Carga / Drag & Drop y Progreso
        self.drop_card = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_DROPZONE,
            corner_radius=14,
            border_width=2,
            border_color=self.COLOR_DROPZONE_BORDER,
        )
        self.drop_card.grid(row=1, column=0, padx=24, pady=10, sticky="ew")
        self.drop_card.grid_columnconfigure(0, weight=1)

        self.drop_title = ctk.CTkLabel(
            self.drop_card,
            text="📄 Selecciona o arrastra tu documento de investigación",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=self.COLOR_TEXT_MAIN,
        )
        self.drop_title.grid(row=0, column=0, padx=20, pady=(18, 4))

        self.drop_hint = ctk.CTkLabel(
            self.drop_card,
            text="Formatos soportados: .PDF  •  .DOCX  •  .HTML  •  .TXT (100% Offline)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
        )
        self.drop_hint.grid(row=1, column=0, padx=20, pady=(0, 12))

        self.btn_select = ctk.CTkButton(
            self.drop_card,
            text="Seleccionar Documento",
            height=38,
            width=210,
            corner_radius=8,
            fg_color=self.COLOR_PRIMARY,
            hover_color=self.COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.seleccionar_archivo,
        )
        self.btn_select.grid(row=2, column=0, padx=20, pady=(0, 14))

        # Barra de progreso e indicador de estado
        self.progress_bar = ctk.CTkProgressBar(
            self.drop_card,
            height=6,
            corner_radius=3,
            progress_color=self.COLOR_PRIMARY,
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=3, column=0, padx=28, pady=(0, 8), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.drop_card,
            text="Listo para procesar documentos.",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.STATUS_IDLE,
        )
        self.status_label.grid(row=4, column=0, padx=20, pady=(0, 14))

        # 3. Panel de Previsualización y Acciones Rápidas
        self.preview_card = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=self.COLOR_DROPZONE_BORDER,
        )
        self.preview_card.grid(row=2, column=0, padx=24, pady=(6, 20), sticky="nsew")
        self.preview_card.grid_columnconfigure(0, weight=1)
        self.preview_card.grid_rowconfigure(1, weight=1)

        # Barra de herramientas del visor
        self.toolbar_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.toolbar_frame.grid(row=0, column=0, padx=16, pady=(12, 8), sticky="ew")
        self.toolbar_frame.grid_columnconfigure(0, weight=1)

        self.preview_title = ctk.CTkLabel(
            self.toolbar_frame,
            text="Vista Previa del Resultado",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.COLOR_TEXT_MAIN,
        )
        self.preview_title.grid(row=0, column=0, sticky="w")

        self.metrics_label = ctk.CTkLabel(
            self.toolbar_frame,
            text="0 caracteres  |  ~0 tokens",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_TEXT_MUTED,
        )
        self.metrics_label.grid(row=0, column=1, padx=12)

        actions_container = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        actions_container.grid(row=0, column=2, sticky="e")

        self.btn_copy = ctk.CTkButton(
            actions_container,
            text="📋 Copiar Markdown",
            height=30,
            width=145,
            corner_radius=6,
            fg_color=self.COLOR_SECONDARY,
            hover_color=self.COLOR_SECONDARY_HOVER,
            text_color=self.COLOR_TEXT_MAIN,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            state="disabled",
            command=self.copiar_portapapeles,
        )
        self.btn_copy.pack(side="left", padx=(0, 8))

        self.btn_open_folder = ctk.CTkButton(
            actions_container,
            text="📂 Abrir carpeta output",
            height=30,
            width=160,
            corner_radius=6,
            fg_color=self.COLOR_SECONDARY,
            hover_color=self.COLOR_SECONDARY_HOVER,
            text_color=self.COLOR_TEXT_MAIN,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            state="disabled",
            command=self.abrir_carpeta_output,
        )
        self.btn_open_folder.pack(side="left")

        # Visor de texto Markdown en modo solo lectura
        self.preview_textbox = ctk.CTkTextbox(
            self.preview_card,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=self.COLOR_BG,
            text_color=self.COLOR_TEXT_MAIN,
            border_width=1,
            border_color=self.COLOR_DROPZONE_BORDER,
            wrap="word",
        )
        self.preview_textbox.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self._actualizar_visor(
            "El contenido Markdown limpio y su bloque YAML Frontmatter aparecerán aquí tras procesar un archivo..."
        )

    def _configurar_drag_and_drop(self) -> None:
        """Registra los eventos de Drag & Drop si tkinterdnd2 está disponible en el entorno."""
        if not CAN_USE_DND:
            self.drop_title.configure(text="📄 Haz clic abajo para seleccionar tu documento")
            return

        try:
            self.drop_card.drop_target_register(DND_FILES)
            self.drop_card.dnd_bind("<<Drop>>", self.al_arrastrar_archivo)
        except Exception:
            self.drop_title.configure(text="📄 Haz clic abajo para seleccionar tu documento")

    def _cambiar_tema(self, valor: str) -> None:
        """Actualiza el modo de apariencia visual de CustomTkinter."""
        mapa = {"Sistema": "System", "Claro": "Light", "Oscuro": "Dark"}
        ctk.set_appearance_mode(mapa.get(valor, "System"))

    @staticmethod
    def _extraer_primera_ruta_dnd(raw_data: str) -> str:
        """
        Extrae la primera ruta válida desde el payload de `tkinterdnd2`,
        soportando rutas con espacios encerradas entre llaves `{...}`.
        """
        if not raw_data:
            return ""
        coincidencias = re.findall(r"\{([^}]+)\}|(\S+)", raw_data.strip())
        for con_llaves, sin_llaves in coincidencias:
            candidata = (con_llaves or sin_llaves).strip()
            if candidata:
                return candidata
        return raw_data.strip("{}")

    def al_arrastrar_archivo(self, event: object) -> None:
        """Manejador del evento `<<Drop>>` al soltar un archivo en la interfaz."""
        if self._procesando:
            return
        datos = getattr(event, "data", "")
        ruta_str = self._extraer_primera_ruta_dnd(datos)
        if ruta_str:
            self.iniciar_procesamiento(Path(ruta_str))

    def seleccionar_archivo(self) -> None:
        """Abre el diálogo nativo para elegir un archivo compatible."""
        if self._procesando:
            return
        filepath = filedialog.askopenfilename(
            title="Seleccionar documento para convertir a Markdown",
            filetypes=[
                ("Documentos soportados", "*.pdf *.docx *.html *.htm *.txt"),
                ("Documentos PDF", "*.pdf"),
                ("Documentos Word", "*.docx"),
                ("Páginas HTML", "*.html *.htm"),
                ("Archivos de Texto", "*.txt"),
            ],
        )
        if filepath:
            self.iniciar_procesamiento(Path(filepath))

    def iniciar_procesamiento(self, ruta_origen: Path) -> None:
        """
        Valida el archivo de entrada y lanza la conversión en un hilo secundario
        para mantener la interfaz gráfica fluida y receptiva.
        """
        if self._procesando:
            return

        if not ruta_origen.is_file():
            self._mostrar_error(f"El archivo no existe: {ruta_origen.name}")
            return

        extension = ruta_origen.suffix.lower()
        if extension not in EXTENSIONES_PERMITIDAS:
            formatos = ", ".join(sorted(EXTENSIONES_PERMITIDAS))
            self._mostrar_error(f"Formato '{extension}' no soportado. Usa: {formatos}")
            return

        # Preparar estado visual de carga
        self._procesando = True
        self.btn_select.configure(state="disabled", text="Procesando...")
        self.btn_copy.configure(state="disabled")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.status_label.configure(
            text=f"⏳ Procesando '{ruta_origen.name}'...",
            text_color=self.STATUS_LOADING,
        )

        # Ejecutar conversión pesada en un hilo worker daemon
        hilo = threading.Thread(
            target=self._ejecutar_conversion_worker,
            args=(ruta_origen,),
            daemon=True,
        )
        hilo.start()

    def _obtener_converter(self) -> MarkItDown:
        """Inicializa perezosamente la instancia de MarkItDown."""
        if self._converter is None:
            self._converter = MarkItDown()
        return self._converter

    def _ejecutar_conversion_worker(self, ruta_origen: Path) -> None:
        """
        Lógica de extracción, limpieza, generación de metadatos y escritura en disco.
        Se ejecuta exclusivamente en un hilo en segundo plano.
        """
        try:
            converter = self._obtener_converter()
            resultado = converter.convert(str(ruta_origen))
            contenido_raw = resultado.text_content or ""

            if not contenido_raw.strip():
                raise ValueError(
                    "El documento no contiene texto extraíble (puede ser un PDF escaneado sin OCR)."
                )

            # Limpieza de ruido y generación de metadatos YAML
            contenido_limpio = limpiar_texto(contenido_raw)
            header = generar_frontmatter(ruta_origen, texto_limpio=contenido_limpio)
            contenido_final = f"{header}{contenido_limpio}"

            # Escritura segura en la carpeta output/
            self.directorio_salida.mkdir(parents=True, exist_ok=True)
            ruta_destino = self.directorio_salida / f"{ruta_origen.stem}.md"
            ruta_destino.write_text(contenido_final, encoding="utf-8")

            tokens_aprox = estimar_tokens(contenido_final)
            self.after(
                0,
                self._finalizar_exito,
                ruta_destino,
                contenido_final,
                tokens_aprox,
            )
        except Exception as exc:
            mensaje_error = str(exc) or exc.__class__.__name__
            self.after(0, self._mostrar_error, mensaje_error)

    def _finalizar_exito(
        self,
        ruta_destino: Path,
        contenido_final: str,
        tokens_aprox: int,
    ) -> None:
        """Actualiza la interfaz en el hilo principal tras completar la conversión."""
        self._procesando = False
        self._ultimo_markdown = contenido_final

        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1.0)

        self.btn_select.configure(state="normal", text="Seleccionar Documento")
        self.btn_copy.configure(state="normal", text="📋 Copiar Markdown")
        self.btn_open_folder.configure(state="normal")

        self.status_label.configure(
            text=f"✔ Guardado con éxito en: output/{ruta_destino.name}",
            text_color=self.STATUS_SUCCESS,
        )
        self.metrics_label.configure(
            text=f"{len(contenido_final):,} caracteres  |  ~{tokens_aprox:,} tokens"
        )
        self._actualizar_visor(contenido_final)

    def _mostrar_error(self, mensaje: str) -> None:
        """Restaura el estado interactivo y muestra un mensaje de error claro."""
        self._procesando = False
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0.0)

        self.btn_select.configure(state="normal", text="Seleccionar Documento")
        self.status_label.configure(
            text=f"✖ Error al procesar: {mensaje}",
            text_color=self.STATUS_ERROR,
        )

    def _actualizar_visor(self, texto: str) -> None:
        """Reemplaza el texto del visor manteniendo el modo de solo lectura."""
        self.preview_textbox.configure(state="normal")
        self.preview_textbox.delete("1.0", "end")
        self.preview_textbox.insert("1.0", texto)
        self.preview_textbox.configure(state="disabled")

    def copiar_portapapeles(self) -> None:
        """Copia el contenido Markdown generado al portapapeles del sistema."""
        if not self._ultimo_markdown:
            return
        self.clipboard_clear()
        self.clipboard_append(self._ultimo_markdown)
        self.update_idletasks()

        self.btn_copy.configure(text="✔ ¡Copiado!")
        self.after(2000, lambda: self.btn_copy.configure(text="📋 Copiar Markdown"))

    def abrir_carpeta_output(self) -> None:
        """Abre el directorio `output` en el explorador de archivos nativo del sistema operativo."""
        self.directorio_salida.mkdir(parents=True, exist_ok=True)
        ruta_str = str(self.directorio_salida.resolve())
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta_str)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta_str])
            else:
                subprocess.Popen(["xdg-open", ruta_str])
        except Exception as exc:
            self._mostrar_error(f"No se pudo abrir la carpeta: {exc}")

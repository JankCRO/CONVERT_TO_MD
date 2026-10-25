# CONVERT_TO_MD 📄➡️📝

![Versión](https://img.shields.io/badge/versi%C3%B3n-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Licencia](https://img.shields.io/badge/licencia-MIT-green)
![Estado](https://img.shields.io/badge/100%25-Offline-success)

**CONVERT_TO_MD** es una aplicación de escritorio **100% local** diseñada para convertir documentos de investigación y trabajo (`.pdf`, `.docx`, `.html`, `.htm`, `.txt`) en archivos **Markdown (`.md`)** limpios y estandarizados.

Su propósito central es optimizar documentos para su ingesta en ventanas de contexto de **LLMs (Claude, ChatGPT, Gemini, modelos locales)**, inyectando automáticamente metadatos estructurados en formato **YAML Frontmatter** y eliminando el ruido de formato para reducir el consumo innecesario de tokens.

---

##  Características Principales

-  **Procesamiento 100% Local y Privado:** Ningún documento se sube a la nube ni consume APIs externas. Ideal para documentos confidenciales o académicos.
-  **Limpieza Inteligente de Ruido (`src/cleaner.py`):**
  - Elimina numeraciones repetitivas (`Página X de Y`, `Page X of Y`) y números de página aislados.
  - Suprime caracteres de control invisibles, saltos de página (`\f`) y colapsa líneas en blanco redundantes.
  - **Preserva la estructura Markdown:** Protege bloques de código cercados (` ``` `) y mantiene la indentación de listas anidadas.
-  **Inyección de YAML Frontmatter (`src/metadata.py`):**
  - Añade una cabecera estándar con `archivo_origen`, `formato_origen`, `fecha_procesamiento`, `tamano_origen_kb`, `caracteres_md`, `tokens_estimados` y `procesado_por`.
-  **Interfaz Moderna y Multithreading (`src/app.py`):**
  - Construida con **CustomTkinter** y soporte **Drag & Drop** (`tkinterdnd2`).
  - Selector de tema en tiempo real (**Sistema / Claro / Oscuro**).
  - Procesamiento asíncrono en hilos secundarios (`threading`) con barra de progreso animada para evitar bloqueos de la interfaz en archivos pesados.
  - **Visor de Vista Previa integrado**, contador de caracteres/tokens estimados, botón de copiado rápido al portapapeles y acceso directo a la carpeta `output/`.

---

##  Stack Tecnológico

| Componente | Tecnología |
| :--- | :--- |
| **Lenguaje** | Python 3.11+ |
| **Gestor de Entorno y Paquetes** | [`uv`](https://docs.astral.sh/uv/) |
| **Interfaz Gráfica (GUI)** | `CustomTkinter` + `tkinterdnd2` |
| **Motor de Extracción** | `MarkItDown` + `magika` + `pdfminer.six` / `pypdf` / `python-docx` |
| **Metadatos** | `PyYAML` |
| **Empaquetado** | `PyInstaller` |

---

##  Estructura del Proyecto

```text
CONVERT_TO_MD/
├── src/
│   ├── app.py               # Interfaz gráfica CustomTkinter, Drag & Drop y worker threads
│   ├── cleaner.py           # Motor de limpieza por expresiones regulares y normalización
│   └── metadata.py          # Generador de YAML Frontmatter y estimador de tokens
├── main.py                  # Punto de entrada principal de la aplicación
├── file_version_info.txt    # Metadatos de versión para el ejecutable de Windows
├── pyproject.toml           # Definición del proyecto y dependencias gestionadas con uv
├── LICENSE                  # Licencia MIT
└── README.md                # Documentación oficial
```

---

##  Instalación y Ejecución en Desarrollo

### Prerrequisitos
- Contar con [**uv**](https://docs.astral.sh/uv/getting-started/installation/) instalado en el sistema.

### Pasos
1. Clonar el repositorio:
   ```powershell
   git clone https://github.com/tu-usuario/CONVERT_TO_MD.git
   cd CONVERT_TO_MD
   ```

2. Sincronizar el entorno virtual e instalar las dependencias:
   ```powershell
   uv sync
   ```

3. Ejecutar la aplicación:
   ```powershell
   uv run main.py
   ```

---

##  Compilación del Ejecutable para Windows (PyInstaller)

Para generar la distribución ejecutable de Windows (`dist/CONVERT_TO_MD/CONVERT_TO_MD.exe`) incluyendo los modelos internos de `magika`, los conversores de `markitdown`, los binarios de `tkinterdnd2`, los temas de `customtkinter` y los metadatos de versión de Windows:

```powershell
uv run pyinstaller --noconfirm --onedir --windowed --name "CONVERT_TO_MD" --version-file "file_version_info.txt" --collect-all magika --collect-all markitdown --collect-all tkinterdnd2 --collect-all customtkinter main.py
```

Una vez finalizada la compilación, el ejecutable estará disponible en:
```text
dist/CONVERT_TO_MD/CONVERT_TO_MD.exe
```

---

##  Seguridad, SmartScreen y Verificación SHA-256

### Aviso sobre Windows Defender SmartScreen
Dado que **CONVERT_TO_MD** es un proyecto de código abierto distribuido sin un certificado comercial de firma de código (*Code Signing Certificate* de pago), al ejecutar `CONVERT_TO_MD.exe` por primera vez en Windows es posible que aparezca la ventana **"Windows protegió su PC" (Microsoft Defender SmartScreen)**.

Para continuar de forma segura:
1. Haz clic en **"Más información"** (*More info*).
2. Presiona el botón **"Ejecutar de todas formas"** (*Run anyway*).

### Verificación de Integridad por Hash SHA-256
Puedes comprobar la integridad del binario compilado o descargado calculando su huella criptográfica **SHA-256**:

- **En Windows (PowerShell):**
  ```powershell
  Get-FileHash -Path ".\dist\CONVERT_TO_MD\CONVERT_TO_MD.exe" -Algorithm SHA256
  ```

- **En Windows (CMD / CertUtil):**
  ```cmd
  certutil -hashfile dist\CONVERT_TO_MD\CONVERT_TO_MD.exe SHA256
  ```

- **En Linux / macOS:**
  ```bash
  sha256sum dist/CONVERT_TO_MD/CONVERT_TO_MD.exe
  ```

---

## Licencia

Distribuido bajo la licencia **MIT**. Consulta el archivo [`LICENSE`](./LICENSE) para más detalles.

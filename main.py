import sys
from src.app import ConvertToMDApp


def main() -> int:
    """Punto de entrada principal de la aplicación CONVERT_TO_MD."""
    app = ConvertToMDApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

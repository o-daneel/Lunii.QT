import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale

from pkg.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("WindowsVista")   # ou "fusion", "Windows", "macos", "gtk"

    translator = QTranslator(app)
    locale = QLocale.system().name()  # e.g., 'fr_FR'
    # locale = "fr_FR"
    path = ':/translations/locales'
    if translator.load(f"{path}/{locale}.qm"):
        app.installTranslator(translator)

    window = MainWindow(app)
    window.show()

    sys.exit(app.exec())

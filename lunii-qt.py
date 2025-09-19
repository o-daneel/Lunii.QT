import sys
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator, QLocale

from pkg.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication([])

    translator = QTranslator(app)
    locale = QLocale.system().name()  # e.g., 'fr_FR'
    # locale = "fr_FR"
    path = ':/translations/locales'
    if translator.load(f"{path}/{locale}.qm"):
        app.installTranslator(translator)

    window = MainWindow(app)
    window.show()

    # killing splash
    try:
        import pyi_splash
        pyi_splash.update_text('Lunii.QT Ready ...')
        time.sleep(0.5)
        pyi_splash.close()
    except:
        pass

    sys.exit(app.exec())

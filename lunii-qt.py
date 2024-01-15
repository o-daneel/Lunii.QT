import sys
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from pkg.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication([])

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

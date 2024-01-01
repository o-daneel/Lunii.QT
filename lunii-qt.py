import sys
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from pkg.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication([])

    # splashscreen
    pixmap = QPixmap(":/img/res/lunii_splash.png").scaledToWidth(256, Qt.SmoothTransformation)
    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.SplashScreen | Qt.WindowStaysOnTopHint)
    splash.show()

    window = MainWindow(app)
    window.show()

    # killing splash
    app.processEvents()
    time.sleep(1)
    splash.finish(window)

    sys.exit(app.exec())

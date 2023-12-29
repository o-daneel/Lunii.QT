import sys
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from pkg.api.stories import story_load_db
from pkg.main_window import MainWindow
import resources_rc


if __name__ == "__main__":
    app = QApplication([])

    # splashscreen
    pixmap = QPixmap(":/img/res/lunii_splash.png").scaledToWidth(256, Qt.SmoothTransformation)
    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.SplashScreen | Qt.WindowStaysOnTopHint)
    splash.show()

    # loading DB
    story_load_db(True)

    window = MainWindow(app)
    window.show()

    time.sleep(2)
    splash.finish(window)

    sys.exit(app.exec())

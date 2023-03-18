import sys

from PySide6.QtWidgets import QApplication

from pkg.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication([])


    window = MainWindow(app)
    window.show()
    sys.exit(app.exec())
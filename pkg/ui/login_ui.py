from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("LuniiStore credentials")
        icon = QIcon()
        icon.addFile(u":/icon/res/logo.ico", QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.setMinimumSize(QSize(200, 0))

        layout = QVBoxLayout(self)

        self.login_label = QLabel("Email:", self)
        self.login_edit = QLineEdit(self)
        layout.addWidget(self.login_label)
        layout.addWidget(self.login_edit)

        self.password_label = QLabel("Password:", self)
        self.password_edit = QLineEdit(self)
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_edit)

        login_button = QPushButton("Login", self)
        login_button.clicked.connect(self.accept)

        layout.addWidget(login_button)

    def get_login_password(self):
        login = self.login_edit.text()
        password = self.password_edit.text()
        return login, password
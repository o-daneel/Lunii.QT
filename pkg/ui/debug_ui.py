# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'debug.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QSizePolicy, QTextEdit, QVBoxLayout, QWidget)
import resources_rc


class DebugDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Debug Log")
        icon = QIcon()
        icon.addFile(u":/icon/res/debug_log.png", QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.setMinimumSize(QSize(500, 0))
        self.resize(500, 300)

        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.textEdit = QTextEdit(self)
        self.textEdit.setObjectName(u"textEdit")
        self.textEdit.setLineWrapMode(QTextEdit.NoWrap)
        self.textEdit.setReadOnly(True)
        self.textEdit.setPlaceholderText("Application Log Empty ...")

        self.verticalLayout.addWidget(self.textEdit)

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close|QDialogButtonBox.Reset|QDialogButtonBox.Save)
        # callbacks on butttons
        self.buttonBox.clicked.connect(self.button_clicked)

        self.verticalLayout.addWidget(self.buttonBox)


    def button_clicked(self, button: QAbstractButton):
        button_role = self.sender().buttonRole(button)

        if button_role == QDialogButtonBox.RejectRole:
            # print("close")
            self.hide()
        elif button_role == QDialogButtonBox.ResetRole:
            self.textEdit.clear()
            # print("reset")
        elif button_role == QDialogButtonBox.AcceptRole:
            print("save")

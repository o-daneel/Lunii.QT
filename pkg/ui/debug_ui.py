import logging

from PySide6.QtCore import (QSize, Qt)
from PySide6.QtGui import (QIcon)
from PySide6.QtWidgets import (QAbstractButton, QDialogButtonBox,
                               QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QLineEdit,
                               QPlainTextEdit, QFileDialog, QSpacerItem, QSizePolicy)

LUNII_LOGGER = "lunii-qt"


class QTextEditHandler(logging.Handler):
    def __init__(self, text_edit):
        super(QTextEditHandler, self).__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.appendPlainText(msg)


class DebugDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.logger = logging.getLogger(LUNII_LOGGER)
        self.logger.setLevel(logging.DEBUG)

        # window config
        self.setWindowTitle("Debug Log")
        icon = QIcon()
        icon.addFile(u":/icon/res/debug_log.png", QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.setMinimumSize(QSize(500, 0))
        self.resize(500, 300)

        # contents
        self.cb_level = QComboBox(self)
        self.le_filter = QLineEdit(self)
        self.le_filter.setClearButtonEnabled(True)
        self.le_filter.setPlaceholderText("(Log filter text)")

        horizontalSpacer = QSpacerItem(80, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)

        upper_layout = QHBoxLayout()
        upper_layout.addWidget(self.cb_level)
        upper_layout.addItem(horizontalSpacer)
        upper_layout.addWidget(self.le_filter)

        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.te_Logger = QPlainTextEdit(self)
        self.te_Logger.setObjectName(u"textEdit")
        self.te_Logger.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.te_Logger.setReadOnly(True)
        self.te_Logger.setPlaceholderText("Application Log Empty ...")

        # adding contents to vertical layout
        self.verticalLayout.addLayout(upper_layout)
        self.verticalLayout.addWidget(self.te_Logger)

        # buttons at bottom
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close|QDialogButtonBox.Reset|QDialogButtonBox.Save)
        # callbacks on buttons
        self.buttonBox.clicked.connect(self.button_clicked)

        self.verticalLayout.addWidget(self.buttonBox)

        # next UI inits
        self.init_ui()

    def init_ui(self):
        self.modify_widgets()
        self.setup_connections()

    def modify_widgets(self):
        self.cb_level.setVisible(True)
        self.cb_level.addItem("DEBUG")
        self.cb_level.addItem("INFO")
        self.cb_level.addItem("WARNING")
        self.cb_level.addItem("ERROR")

        self.cb_level.setCurrentIndex(1)
        self.logger.setLevel(logging.INFO)

        self.le_filter.setVisible(True)
        self.le_filter.setEnabled(False)

    def setup_connections(self):
        # log level selector
        self.cb_level.currentIndexChanged.connect(self.cb_level_selected)

        # connecting logger handler
        handler = QTextEditHandler(self.te_Logger)
        handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        self.logger.addHandler(handler)

    def cb_level_selected(self):
        # getting current device
        dict_level = { "DEBUG": logging.DEBUG,
                       "INFO": logging.INFO,
                       "WARNING": logging.WARNING,
                       "ERROR": logging.ERROR}

        level = self.cb_level.currentText()
        self.logger.setLevel(dict_level[level])

    def button_clicked(self, button: QAbstractButton):
        button_role = self.sender().buttonRole(button)

        if button_role == QDialogButtonBox.RejectRole:
            self.hide()
        elif button_role == QDialogButtonBox.ResetRole:
            self.te_Logger.clear()
        elif button_role == QDialogButtonBox.AcceptRole:
            self.save_log()

    def save_log(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "Text Files (*.txt);;All Files (*)")
        if filename:
            with open(filename, 'wb') as file:
                file.write(self.te_Logger.toPlainText().encode('utf-8'))

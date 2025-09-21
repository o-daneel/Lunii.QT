from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtWidgets import QMessageBox

LUNIIQT_ABOUT_INFO_HTML = """
<h2><b>Lunii Qt-Manager</b></h2>
<br />


This application is a PoC that allows to manage the contents of your own Lunii Storyteller,
including changing stories order, backup (for personal usage only), restore, and downloading 
your latest Lunii firmware (to eventually restore from a broken device).<br />
  
<br />Powered by Python 3.11, PySide 6<br />
<br />

Icons are provided freely by <a href="www.icons8.com">icon8</a><br />
 
Logos are provided by <b>malexxx</b><br /><br />

<b>URL : </b><a href="https://github.com/o-daneel/Lunii.QT">https://github.com/o-daneel/Lunii.QT</a>
"""


def about_dlg(parent=None):
    msg_box = QMessageBox(QMessageBox.Information, "About", LUNIIQT_ABOUT_INFO_HTML, QMessageBox.Ok, parent)

    icon = QtGui.QIcon()
    icon.addPixmap(QtGui.QPixmap(":/icon/res/about.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
    msg_box.setWindowIcon(icon)

    pixmap = QtGui.QPixmap(":/img/res/lunii_about.png").scaledToHeight(220, QtCore.Qt.SmoothTransformation)
    msg_box.setIconPixmap(pixmap)

    layout = msg_box.layout()
    widget = QtWidgets.QWidget()
    widget.setFixedSize(550, 1)
    layout.addWidget(widget, 3, 0, 1, 3)

    msg_box.exec()

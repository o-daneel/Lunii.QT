# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'nm.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_nightMode(object):
    def setupUi(self, nightMode):
        if not nightMode.objectName():
            nightMode.setObjectName(u"nightMode")
        nightMode.resize(400, 390)
        nightMode.setMinimumSize(QSize(400, 0))
        nightMode.setModal(True)
        self.verticalLayout = QVBoxLayout(nightMode)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lbl_Header = QLabel(nightMode)
        self.lbl_Header.setObjectName(u"lbl_Header")
        self.lbl_Header.setAlignment(Qt.AlignCenter)
        self.lbl_Header.setMargin(10)

        self.verticalLayout.addWidget(self.lbl_Header)

        self.groupBox = QGroupBox(nightMode)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.hl_nm_mode = QHBoxLayout()
        self.hl_nm_mode.setObjectName(u"hl_nm_mode")
        self.lbl_enable = QLabel(self.groupBox)
        self.lbl_enable.setObjectName(u"lbl_enable")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_enable.sizePolicy().hasHeightForWidth())
        self.lbl_enable.setSizePolicy(sizePolicy)

        self.hl_nm_mode.addWidget(self.lbl_enable)

        self.cbox_enable = QCheckBox(self.groupBox)
        self.cbox_enable.setObjectName(u"cbox_enable")
        sizePolicy1 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.cbox_enable.sizePolicy().hasHeightForWidth())
        self.cbox_enable.setSizePolicy(sizePolicy1)
        self.cbox_enable.setText(u"")

        self.hl_nm_mode.addWidget(self.cbox_enable)


        self.verticalLayout_2.addLayout(self.hl_nm_mode)

        self.line_2 = QFrame(self.groupBox)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.HLine)
        self.line_2.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_2.addWidget(self.line_2)

        self.hl_volume = QHBoxLayout()
        self.hl_volume.setObjectName(u"hl_volume")
        self.lbl_limit = QLabel(self.groupBox)
        self.lbl_limit.setObjectName(u"lbl_limit")
        sizePolicy.setHeightForWidth(self.lbl_limit.sizePolicy().hasHeightForWidth())
        self.lbl_limit.setSizePolicy(sizePolicy)

        self.hl_volume.addWidget(self.lbl_limit)

        self.cbox_limit = QCheckBox(self.groupBox)
        self.cbox_limit.setObjectName(u"cbox_limit")
        sizePolicy1.setHeightForWidth(self.cbox_limit.sizePolicy().hasHeightForWidth())
        self.cbox_limit.setSizePolicy(sizePolicy1)
        self.cbox_limit.setText(u"")

        self.hl_volume.addWidget(self.cbox_limit)


        self.verticalLayout_2.addLayout(self.hl_volume)

        self.lbl_desc_limit = QLabel(self.groupBox)
        self.lbl_desc_limit.setObjectName(u"lbl_desc_limit")
        self.lbl_desc_limit.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.lbl_desc_limit)

        self.line = QFrame(self.groupBox)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_2.addWidget(self.line)

        self.hl_autoplay = QHBoxLayout()
        self.hl_autoplay.setObjectName(u"hl_autoplay")
        self.lbl_autoplay = QLabel(self.groupBox)
        self.lbl_autoplay.setObjectName(u"lbl_autoplay")
        sizePolicy.setHeightForWidth(self.lbl_autoplay.sizePolicy().hasHeightForWidth())
        self.lbl_autoplay.setSizePolicy(sizePolicy)

        self.hl_autoplay.addWidget(self.lbl_autoplay)

        self.cbox_autoplay = QCheckBox(self.groupBox)
        self.cbox_autoplay.setObjectName(u"cbox_autoplay")
        self.cbox_autoplay.setText(u"")

        self.hl_autoplay.addWidget(self.cbox_autoplay)


        self.verticalLayout_2.addLayout(self.hl_autoplay)

        self.lbl_desc_autoplay = QLabel(self.groupBox)
        self.lbl_desc_autoplay.setObjectName(u"lbl_desc_autoplay")
        self.lbl_desc_autoplay.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.lbl_desc_autoplay)

        self.hl_maxstories = QHBoxLayout()
        self.hl_maxstories.setObjectName(u"hl_maxstories")
        self.lbl_maxstories = QLabel(self.groupBox)
        self.lbl_maxstories.setObjectName(u"lbl_maxstories")
        sizePolicy.setHeightForWidth(self.lbl_maxstories.sizePolicy().hasHeightForWidth())
        self.lbl_maxstories.setSizePolicy(sizePolicy)

        self.hl_maxstories.addWidget(self.lbl_maxstories)

        self.sbox_maxstories = QSpinBox(self.groupBox)
        self.sbox_maxstories.setObjectName(u"sbox_maxstories")
        self.sbox_maxstories.setMinimumSize(QSize(60, 0))
        self.sbox_maxstories.setAlignment(Qt.AlignCenter)
        self.sbox_maxstories.setMinimum(1)
        self.sbox_maxstories.setMaximum(8)
        self.sbox_maxstories.setValue(3)

        self.hl_maxstories.addWidget(self.sbox_maxstories)


        self.verticalLayout_2.addLayout(self.hl_maxstories)

        self.line_3 = QFrame(self.groupBox)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.HLine)
        self.line_3.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_2.addWidget(self.line_3)

        self.hl_sleep = QHBoxLayout()
        self.hl_sleep.setObjectName(u"hl_sleep")
        self.lbl_turnoff = QLabel(self.groupBox)
        self.lbl_turnoff.setObjectName(u"lbl_turnoff")
        sizePolicy.setHeightForWidth(self.lbl_turnoff.sizePolicy().hasHeightForWidth())
        self.lbl_turnoff.setSizePolicy(sizePolicy)

        self.hl_sleep.addWidget(self.lbl_turnoff)

        self.cbox_turnoff_nm = QCheckBox(self.groupBox)
        self.cbox_turnoff_nm.setObjectName(u"cbox_turnoff_nm")
        self.cbox_turnoff_nm.setText(u"")

        self.hl_sleep.addWidget(self.cbox_turnoff_nm)


        self.verticalLayout_2.addLayout(self.hl_sleep)

        self.lbl_desc_turnoff = QLabel(self.groupBox)
        self.lbl_desc_turnoff.setObjectName(u"lbl_desc_turnoff")
        self.lbl_desc_turnoff.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.lbl_desc_turnoff)


        self.verticalLayout.addWidget(self.groupBox)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.hl_button = QHBoxLayout()
        self.hl_button.setObjectName(u"hl_button")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.hl_button.addItem(self.horizontalSpacer)

        self.btn_save = QPushButton(nightMode)
        self.btn_save.setObjectName(u"btn_save")

        self.hl_button.addWidget(self.btn_save)


        self.verticalLayout.addLayout(self.hl_button)


        self.retranslateUi(nightMode)

        QMetaObject.connectSlotsByName(nightMode)
    # setupUi

    def retranslateUi(self, nightMode):
        nightMode.setWindowTitle(QCoreApplication.translate("nightMode", "Night mode settings", None))
        self.lbl_Header.setText(QCoreApplication.translate("nightMode", "<h2>Configure Night Mode</h2>", None))
        self.groupBox.setTitle("")
        self.lbl_enable.setText(QCoreApplication.translate("nightMode", "<h4>Night mode", None))
        self.lbl_limit.setText(QCoreApplication.translate("nightMode", "<h4>Limit Volume", None))
        self.lbl_desc_limit.setText(QCoreApplication.translate("nightMode", "The volume will be kept low for a calm listening experience conducive to falling asleep.", None))
        self.lbl_autoplay.setText(QCoreApplication.translate("nightMode", "<h4>Keep playing with next", None))
        self.lbl_desc_autoplay.setText(QCoreApplication.translate("nightMode", "You can choose how many stories will be read before the device shuts down.", None))
        self.lbl_maxstories.setText(QCoreApplication.translate("nightMode", "Max stories to play", None))
        self.lbl_turnoff.setText(QCoreApplication.translate("nightMode", "<h4>Turn off after sleep", None))
        self.lbl_desc_turnoff.setText(QCoreApplication.translate("nightMode", "By enabling this feature, the device will automatically return to Day Mode after shutting down.", None))
        self.btn_save.setText(QCoreApplication.translate("nightMode", "Save", None))
    # retranslateUi


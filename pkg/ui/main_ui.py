# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLayout,
    QLineEdit, QMainWindow, QProgressBar, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QTextBrowser,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(640, 600)
        icon = QIcon()
        icon.addFile(u":/icon/res/logo.ico", QSize(), QIcon.Normal, QIcon.Off)
        MainWindow.setWindowIcon(icon)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(6)
        self.top_layout.setObjectName(u"top_layout")
        self.btn_refresh = QPushButton(self.centralwidget)
        self.btn_refresh.setObjectName(u"btn_refresh")
        self.btn_refresh.setMaximumSize(QSize(25, 25))
        font = QFont()
        font.setPointSize(9)
        self.btn_refresh.setFont(font)
        icon1 = QIcon()
        icon1.addFile(u":/icon/res/refresh.png", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_refresh.setIcon(icon1)
        self.btn_refresh.setIconSize(QSize(22, 22))
        self.btn_refresh.setFlat(False)

        self.top_layout.addWidget(self.btn_refresh)

        self.combo_device = QComboBox(self.centralwidget)
        self.combo_device.addItem("")
        self.combo_device.addItem("")
        self.combo_device.setObjectName(u"combo_device")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.combo_device.sizePolicy().hasHeightForWidth())
        self.combo_device.setSizePolicy(sizePolicy)
        self.combo_device.setMaximumSize(QSize(200, 16777215))
        self.combo_device.setEditable(True)

        self.top_layout.addWidget(self.combo_device)

        self.horizontalSpacer = QSpacerItem(80, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.top_layout.addItem(self.horizontalSpacer)

        self.le_filter = QLineEdit(self.centralwidget)
        self.le_filter.setObjectName(u"le_filter")
        self.le_filter.setClearButtonEnabled(True)

        self.top_layout.addWidget(self.le_filter)


        self.verticalLayout_2.addLayout(self.top_layout)

        self.tree_stories = QTreeWidget(self.centralwidget)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(1, u"UUID");
        self.tree_stories.setHeaderItem(__qtreewidgetitem)
        font1 = QFont()
        font1.setFamilies([u"Consolas"])
        __qtreewidgetitem1 = QTreeWidgetItem(self.tree_stories)
        __qtreewidgetitem1.setFont(1, font1);
        __qtreewidgetitem2 = QTreeWidgetItem(self.tree_stories)
        __qtreewidgetitem2.setFont(1, font1);
        QTreeWidgetItem(self.tree_stories)
        QTreeWidgetItem(self.tree_stories)
        self.tree_stories.setObjectName(u"tree_stories")
        self.tree_stories.setMinimumSize(QSize(0, 150))
        self.tree_stories.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree_stories.setDragEnabled(True)
        self.tree_stories.setDragDropMode(QAbstractItemView.DragDrop)
        self.tree_stories.setDefaultDropAction(Qt.MoveAction)
        self.tree_stories.setAlternatingRowColors(True)
        self.tree_stories.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree_stories.setIndentation(20)
        self.tree_stories.setRootIsDecorated(True)
        self.tree_stories.setItemsExpandable(True)
        self.tree_stories.setAllColumnsShowFocus(True)

        self.verticalLayout_2.addWidget(self.tree_stories)

        self.progressLayout = QVBoxLayout()
        self.progressLayout.setSpacing(0)
        self.progressLayout.setObjectName(u"progressLayout")
        self.totalLayout = QHBoxLayout()
        self.totalLayout.setSpacing(6)
        self.totalLayout.setObjectName(u"totalLayout")
        self.lbl_total = QLabel(self.centralwidget)
        self.lbl_total.setObjectName(u"lbl_total")
        self.lbl_total.setMinimumSize(QSize(80, 0))
        self.lbl_total.setFrameShape(QFrame.Panel)
        self.lbl_total.setFrameShadow(QFrame.Sunken)
        self.lbl_total.setAlignment(Qt.AlignCenter)

        self.totalLayout.addWidget(self.lbl_total)

        self.pbar_total = QProgressBar(self.centralwidget)
        self.pbar_total.setObjectName(u"pbar_total")
        self.pbar_total.setMaximumSize(QSize(16777215, 10))
        self.pbar_total.setValue(24)
        self.pbar_total.setTextVisible(False)

        self.totalLayout.addWidget(self.pbar_total)


        self.progressLayout.addLayout(self.totalLayout)

        self.storyLayout = QHBoxLayout()
        self.storyLayout.setSpacing(6)
        self.storyLayout.setObjectName(u"storyLayout")
        self.lbl_story = QLabel(self.centralwidget)
        self.lbl_story.setObjectName(u"lbl_story")
        self.lbl_story.setMinimumSize(QSize(80, 0))
        self.lbl_story.setFrameShape(QFrame.Panel)
        self.lbl_story.setFrameShadow(QFrame.Sunken)
        self.lbl_story.setAlignment(Qt.AlignCenter)

        self.storyLayout.addWidget(self.lbl_story)

        self.pbar_story = QProgressBar(self.centralwidget)
        self.pbar_story.setObjectName(u"pbar_story")
        self.pbar_story.setMaximumSize(QSize(16777215, 10))
        self.pbar_story.setValue(24)
        self.pbar_story.setTextVisible(False)

        self.storyLayout.addWidget(self.pbar_story)


        self.progressLayout.addLayout(self.storyLayout)


        self.verticalLayout_2.addLayout(self.progressLayout)

        self.details_layout = QHBoxLayout()
        self.details_layout.setObjectName(u"details_layout")
        self.details_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.lbl_picture = QLabel(self.centralwidget)
        self.lbl_picture.setObjectName(u"lbl_picture")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.lbl_picture.sizePolicy().hasHeightForWidth())
        self.lbl_picture.setSizePolicy(sizePolicy1)
        self.lbl_picture.setMinimumSize(QSize(192, 0))
        font2 = QFont()
        font2.setPointSize(12)
        self.lbl_picture.setFont(font2)
        self.lbl_picture.setAlignment(Qt.AlignCenter)

        self.details_layout.addWidget(self.lbl_picture)

        self.te_story_details = QTextBrowser(self.centralwidget)
        self.te_story_details.setObjectName(u"te_story_details")
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.te_story_details.sizePolicy().hasHeightForWidth())
        self.te_story_details.setSizePolicy(sizePolicy2)
        self.te_story_details.setMaximumSize(QSize(16777215, 192))
        self.te_story_details.setOpenExternalLinks(True)
        self.te_story_details.setOpenLinks(False)

        self.details_layout.addWidget(self.te_story_details)


        self.verticalLayout_2.addLayout(self.details_layout)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        self.statusbar.setLayoutDirection(Qt.LeftToRight)
        MainWindow.setStatusBar(self.statusbar)
        QWidget.setTabOrder(self.combo_device, self.le_filter)
        QWidget.setTabOrder(self.le_filter, self.tree_stories)

        self.retranslateUi(MainWindow)
        self.combo_device.currentIndexChanged.connect(self.tree_stories.clear)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Lunii Qt-Manager", None))
        self.btn_refresh.setText("")
        self.combo_device.setItemText(0, QCoreApplication.translate("MainWindow", u"D:\\", None))
        self.combo_device.setItemText(1, QCoreApplication.translate("MainWindow", u"F:\\", None))

#if QT_CONFIG(tooltip)
        self.combo_device.setToolTip(QCoreApplication.translate("MainWindow", u"Select your Lunii", None))
#endif // QT_CONFIG(tooltip)
        self.combo_device.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Select your Lunii", None))
        self.le_filter.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Type to filter", None))
        ___qtreewidgetitem = self.tree_stories.headerItem()
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"Story Name", None));

        __sortingEnabled = self.tree_stories.isSortingEnabled()
        self.tree_stories.setSortingEnabled(False)
        ___qtreewidgetitem1 = self.tree_stories.topLevelItem(0)
        ___qtreewidgetitem1.setText(1, QCoreApplication.translate("MainWindow", u"C4139D59-872A-4D15-8CF1-76D34CDF38C6", None));
        ___qtreewidgetitem1.setText(0, QCoreApplication.translate("MainWindow", u"Suzanne et Gaston", None));
        ___qtreewidgetitem2 = self.tree_stories.topLevelItem(1)
        ___qtreewidgetitem2.setText(1, QCoreApplication.translate("MainWindow", u"03933BA4-4FBF-475F-9ECC-35EFB4D11DC9", None));
        ___qtreewidgetitem2.setText(0, QCoreApplication.translate("MainWindow", u"Panique aux 6 Royaumes", None));
        ___qtreewidgetitem3 = self.tree_stories.topLevelItem(2)
        ___qtreewidgetitem3.setText(1, QCoreApplication.translate("MainWindow", u"22137B29-8646-4335-8069-4A4C9A2D7E89", None));
        ___qtreewidgetitem3.setText(0, QCoreApplication.translate("MainWindow", u"Au Pays des Loups", None));
        ___qtreewidgetitem4 = self.tree_stories.topLevelItem(3)
        ___qtreewidgetitem4.setText(1, QCoreApplication.translate("MainWindow", u"29264ADF-5A9F-451A-B1EC-2AE21BBA473C", None));
        ___qtreewidgetitem4.setText(0, QCoreApplication.translate("MainWindow", u"Sur les bancs de l'\u00e9cole", None));
        self.tree_stories.setSortingEnabled(__sortingEnabled)

        self.lbl_total.setText(QCoreApplication.translate("MainWindow", u"Total", None))
        self.lbl_story.setText(QCoreApplication.translate("MainWindow", u"8B_UUID", None))
        self.lbl_picture.setText(QCoreApplication.translate("MainWindow", u"Pic", None))
        self.te_story_details.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Story description", None))
    # retranslateUi


import logging
import os.path
import shutil
import time
from pathlib import WindowsPath

import psutil
import requests
from PySide6 import QtCore, QtGui
from PySide6.QtCore import QItemSelectionModel, QUrl
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QPixmap, Qt, QDesktopServices
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QFileDialog, QMessageBox, QLabel, QFrame, QHeaderView, \
    QDialog, QApplication

from pkg.api import constants
from pkg.api.constants import *
from pkg.api.device_flam import is_flam, FlamDevice
from pkg.api.device_lunii import LuniiDevice, is_lunii
from pkg.api.devices import find_devices
from pkg.api.firmware import lunii_get_authtoken, lunii_fw_version, lunii_fw_download
from pkg.api.stories import story_load_db, DESC_NOT_FOUND, StoryList
from pkg.ierWorker import ierWorker, ACTION_REMOVE, ACTION_IMPORT, ACTION_EXPORT, ACTION_SIZE
from pkg.ui.about_ui import about_dlg
from pkg.ui.debug_ui import DebugDialog, LUNII_LOGGER
from pkg.ui.login_ui import LoginDialog
from pkg.ui.main_ui import Ui_MainWindow

COL_NAME = 0
COL_DB = 1
COL_UUID = 2
COL_SIZE = 3

COL_DB_SIZE = 20
COL_UUID_SIZE = 250
COL_SIZE_SIZE = 90

APP_VERSION = "v2.5.4"


class VLine(QFrame):
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        self.logger = logging.getLogger(LUNII_LOGGER)

        self.debug_dialog = DebugDialog()
        self.login_dialog = LoginDialog()
        # self.debug_dialog.show()

        # class instance vars init
        self.audio_device: LuniiDevice = None
        self.worker: ierWorker = None
        self.thread: QtCore.QThread = None
        self.app = app
        # app config
        self.sizes_hidden = True
        self.details_hidden = False
        self.details_last_uuid = None
        self.last_version = None
        self.ffmpeg_present = shutil.which("ffmpeg") is not None

        # actions local storage
        self.act_mv_top = None
        self.act_mv_up = None
        self.act_mv_down = None
        self.act_mv_bottom = None
        self.act_import = None
        self.act_export = None
        self.act_exportall = None
        self.act_remove = None
        self.act_getfw = None
        self.act_update = None

        # loading DB
        story_load_db(False)

        # UI init
        self.app.processEvents()
        self.init_ui()
        self.app.processEvents()

        # fetching last app version on Github
        try:
            headers = {'Referer': f"Lunii.QT {APP_VERSION}"}
            response = requests.get("https://github.com/o-daneel/Lunii.QT/releases/latest", headers=headers, timeout=1)
            self.last_version = response.url.split("/").pop()
            self.logger.log(logging.INFO, f"Latest Github release {self.last_version}")
        except (requests.exceptions.Timeout, requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            pass

        self.cb_menu_help_update()

    def init_ui(self):
        self.setupUi(self)
        self.modify_widgets()
        self.setup_connections()
        self.cb_dev_refresh()

    # update ui elements state (enable, disable, context enu)
    def modify_widgets(self):
        self.setWindowTitle(f"Lunii Qt-Manager {APP_VERSION}")

        self.menuUpdate.setVisible(False)
        self.menuUpdate.setTitle("")

        # self.pgb_total.setVisible(False)

        # QTreeWidget for stories
        self.tree_stories.header().setSectionResizeMode(COL_DB, QHeaderView.Fixed)
        self.tree_stories.header().setSectionResizeMode(COL_UUID, QHeaderView.ResizeToContents)
        # self.tree_stories.setColumnWidth(COL_NAME, 300)
        self.tree_stories.setColumnWidth(COL_DB, COL_DB_SIZE)
        # self.tree_stories.setColumnHidden(COL_DB, True)
        # self.tree_stories.setColumnWidth(COL_UUID, 250)
        self.tree_stories.setColumnHidden(COL_SIZE, self.sizes_hidden)
        # self.tree_stories.setColumnWidth(COL_SIZE, 50)

        self.lbl_picture.setVisible(False)
        self.te_story_details.setVisible(False)

        # clean progress bars
        self.lbl_total.setVisible(False)
        self.pbar_total.setVisible(False)
        self.lbl_story.setVisible(False)
        self.pbar_story.setVisible(False)

        # self.pbar_story.setStyleSheet("""
        #     QProgressBar::chunk {
        #         background-color: #3498db; /* Couleur de la barre de progression */
        #     }
        # """)

        # finding menu actions
        s_actions = self.menuStory.actions()
        self.act_mv_top = next(act for act in s_actions if act.objectName() == "actionMove_Top")
        self.act_mv_up = next(act for act in s_actions if act.objectName() == "actionMove_Up")
        self.act_mv_down = next(act for act in s_actions if act.objectName() == "actionMove_Down")
        self.act_mv_bottom = next(act for act in s_actions if act.objectName() == "actionMove_Bottom")
        self.act_import = next(act for act in s_actions if act.objectName() == "actionImport")
        self.act_export = next(act for act in s_actions if act.objectName() == "actionExport")
        self.act_exportall = next(act for act in s_actions if act.objectName() == "actionExport_All")
        self.act_remove = next(act for act in s_actions if act.objectName() == "actionRemove")

        # Update statusbar
        self.sb_create()

        # Update Menu tools based on config
        t_actions = self.menuTools.actions()
        self.act_getfw = next(act for act in t_actions if act.objectName() == "actionGet_firmware")
        act_transcode = next(act for act in t_actions if act.objectName() == "actionTranscode")
        act_transcode.setChecked(self.ffmpeg_present)
        act_transcode.setText("FFMPEG detected" if self.ffmpeg_present else "FFMPEG is missing")

        act_details = next(act for act in t_actions if act.objectName() == "actionShow_story_details")
        act_size = next(act for act in t_actions if act.objectName() == "actionShow_size")
        act_details.setChecked(not self.details_hidden)
        act_size.setChecked(not self.sizes_hidden)
        # act_log = next(act for act in t_actions if act.objectName() == "actionShow_Log")
        # act_log.setVisible(False)

        # Help Menu
        t_actions = self.menuHelp.actions()
        self.act_update = next(act for act in t_actions if act.objectName() == "actionUpdate")
        self.act_update.setVisible(False)

       # Connect the main window's moveEvent to the custom slot
        self.moveEvent = self.customMoveEvent

    # connecting slots and signals
    def setup_connections(self):
        self.combo_device.currentIndexChanged.connect(self.cb_dev_select)
        self.le_filter.textChanged.connect(self.ts_update)

        self.btn_refresh.clicked.connect(self.cb_dev_refresh)
        self.btn_db.clicked.connect(self.cb_db_refresh)

        self.tree_stories.itemSelectionChanged.connect(self.cb_tree_select)
        self.tree_stories.installEventFilter(self)

        QApplication.instance().focusChanged.connect(self.onFocusChanged)

        # Connect the context menu
        self.tree_stories.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_stories.customContextMenuRequested.connect(self.cb_show_context_menu)

        # connect menu callbacks
        self.menuFile.triggered.connect(self.cb_menu_file)
        self.menuStory.triggered.connect(self.cb_menu_story)
        self.menuStory.aboutToShow.connect(self.cb_menu_story_update)
        self.menuTools.triggered.connect(self.cb_menu_tools)
        self.menuTools.aboutToShow.connect(self.cb_menu_tools_update)
        self.menuHelp.aboutToShow.connect(self.cb_menu_help_update)
        self.menuHelp.triggered.connect(self.cb_menu_help)

        # story list shortcuts
        QShortcut(QKeySequence("F5"), self, self.cb_dev_refresh)
        QShortcut(QKeySequence("F2"), self, toggle_refresh_cache)
        QShortcut(QKeySequence("F1"), self, about_dlg)

    # TREE WIDGET MANAGEMENT
    def eventFilter(self, obj, event):
        if obj.objectName() == "tree_stories":
            if event.type() == QtCore.QEvent.DragEnter:
                self.ts_dragenter_action(event)
                return True
            elif event.type() == QtCore.QEvent.Drop:
                self.ts_drop_action(event)
                return True
            elif event.type() == QtCore.QEvent.Resize:
                # Adjusting cols based on widget size
                if not self.sizes_hidden:
                    col_size_width = self.tree_stories.width() - COL_DB_SIZE - self.tree_stories.columnWidth(COL_UUID) - COL_SIZE_SIZE
                    self.tree_stories.setColumnWidth(COL_NAME, col_size_width)
                    self.tree_stories.setColumnWidth(COL_SIZE, COL_SIZE_SIZE - 30)
                else:
                    col_size_width = self.tree_stories.width() - COL_DB_SIZE - COL_UUID_SIZE
                    self.tree_stories.setColumnWidth(COL_UUID, COL_UUID_SIZE)
                    self.tree_stories.setColumnWidth(COL_NAME, col_size_width - 30)

        return False


    def customMoveEvent(self, event):
        # This custom slot is called when the main window is moved
        if self.debug_dialog.isVisible():
            # Move the sub-window alongside the main window
            main_window_rect = self.geometry()
            sub_window_rect = self.debug_dialog.geometry()

            sub_window_rect.moveTopLeft(main_window_rect.topRight() + QtCore.QPoint(5, 0))
            self.debug_dialog.setGeometry(sub_window_rect)

        # Call the default moveEvent implementation
        super().moveEvent(event)

    def onFocusChanged(self, old, now):
        if not self.isHidden() and not old and now:
            self.raise_()
        if not self.debug_dialog.isHidden() and not old and now:
            self.debug_dialog.raise_()
        if not self.login_dialog.isHidden() and not old and now:
            self.login_dialog.raise_()

    def closeEvent(self, event):
        # Explicitly close the log window when the main window is closed
        self.debug_dialog.close()
        event.accept()

    def cb_show_context_menu(self, point):
        # change active menu based on selection
        self.cb_menu_story_update()

        self.menuStory.exec_(self.tree_stories.mapToGlobal(point))

    # WIDGETS UPDATES
    def cb_dev_refresh(self):
        dev_list = find_devices()
        self.combo_device.clear()
        self.audio_device = None

        dev: WindowsPath
        self.combo_device.setPlaceholderText("Select your Lunii")
        self.sb_update("")

        for dev in dev_list:
            dev_name = str(dev)
            # print(dev_name)
            self.combo_device.addItem(dev_name)

        if os.path.isdir("C:/Work/dev/lunii-sd/"):
            self.combo_device.addItem("C:/Work/dev/lunii-sd/")
            self.combo_device.addItem("C:/Work/dev/lunii-sd/_flam/")
            self.combo_device.addItem("C:/Work/dev/lunii-sd/_v1/")
            self.combo_device.addItem("C:/Work/dev/lunii-sd/_v1/")
            self.combo_device.addItem("C:/Work/dev/lunii-sd/_v2/")
            self.combo_device.addItem("C:/Work/dev/lunii-sd/_v3/")

        if self.combo_device.count():
            self.combo_device.setPlaceholderText("Select your Lunii")

            # automatic select if only one device
            if self.combo_device.count() == 1:
                self.combo_device.setCurrentIndex(0)
        else:
            self.statusbar.showMessage("No Lunii detected 😥, try File/Open")
            self.combo_device.setPlaceholderText("No Lunii detected 😥")

    def cb_dev_select(self):
        # getting current device
        dev_name = self.combo_device.currentText()

        if dev_name:
            if not is_lunii(dev_name) and not is_flam(dev_name):
                self.logger.log(logging.ERROR, f"{dev_name} is not a recognized device.")

                # removing the new entry
                cur_index = self.combo_device.currentIndex()
                self.combo_device.setCurrentIndex(-1)
                self.combo_device.removeItem(cur_index)
                return

            # in case of a worker, abort it
            if self.worker:
                self.worker.early_exit = True
                while self.worker:
                    self.app.processEvents()
                    time.sleep(0.05)

            if is_lunii(dev_name):
                self.audio_device = LuniiDevice(dev_name, V3_KEYS)
            else:
                self.audio_device = FlamDevice(dev_name)
            self.statusbar.showMessage(f"")

            self.ts_update()
            self.sb_update("")

            # computing sizes if necessary
            if not self.sizes_hidden and any(story for story in self.audio_device.stories if story.size == -1):
                self.worker_launch(ACTION_SIZE)

    def cb_tree_select(self):
        # getting selection
        selection = self.tree_stories.selectedItems()
        show_details = len(selection) == 1 and not self.details_hidden
        self.te_story_details.setVisible(show_details)
        self.lbl_picture.setVisible(show_details)

        if show_details:
            item = selection[0]
            uuid = item.text(COL_UUID)

            # early exit if no changes on story
            if uuid == self.details_last_uuid:
                return

            # keeping track of currently displayed story
            self.details_last_uuid = uuid

            # feeding story image and desc
            one_story = self.audio_device.stories.get_story(uuid)
            if not one_story:
                return
            one_story_desc = one_story.desc
            one_story_image = one_story.get_picture()

            # nothing to display
            if (not one_story_desc or one_story_desc == DESC_NOT_FOUND) and not one_story_image:
                self.te_story_details.setVisible(False)
                self.lbl_picture.setVisible(False)
                return

            # Update story description
            self.te_story_details.setText(one_story_desc)

            # Display image from URL or cache
            if one_story_image:
                pixmap = QPixmap()
                pixmap.loadFromData(one_story_image)

                scaled_pixmap = pixmap.scaled(192, 192, aspectMode=Qt.KeepAspectRatio, mode=Qt.SmoothTransformation)
                self.lbl_picture.setPixmap(scaled_pixmap)
            else:
                self.lbl_picture.setText("Failed to fetch BMP file.")

    def cb_db_refresh(self):
        self.sb_update("Fetching official Lunii DB...")
        self.pbar_total.setVisible(True)
        self.pbar_total.setRange(0,100)
        self.pbar_total.setValue(10)
        self.app.processEvents()

        retVal = story_load_db(True)

        self.pbar_total.setValue(90)
        self.app.processEvents()

        self.ts_update()

        self.pbar_total.setValue(100)
        self.app.processEvents()

        self.pbar_total.setVisible(False)
        if retVal:
            self.sb_update("👍 Lunii DB refreshed.")
        else:
            self.sb_update("🛑 Lunii DB failed.")

    def cb_menu_file(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionOpen_Lunii":

            # file_filter = "Lunii Metadata (.md);;All files (*)"
            # file, _ = QFileDialog.getOpenFileName(self, "Open Lunii device", "", file_filter)
            dev_dir = QFileDialog.getExistingDirectory(self, "Open Lunii device", "",
                                                   QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
            if not dev_dir:
                return

            # check if path is a recognized device
            if not is_lunii(dev_dir):
                self.sb_update("Not a Lunii or unsupported one 😥")
                return

            # add device to list
            device_list = [self.combo_device.itemText(i) for i in range(self.combo_device.count())]
            if dev_dir not in device_list:
                self.combo_device.addItem(dev_dir)
                index = self.combo_device.findText(dev_dir)
                self.combo_device.setCurrentIndex(index)

    def cb_menu_story(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionMove_Top":
            self.ts_move(-10)
        elif act_name == "actionMove_Up":
            self.ts_move(-1)
        elif act_name == "actionMove_Down":
            self.ts_move(1)
        elif act_name == "actionMove_Bottom":
            self.ts_move(10)
        elif act_name == "actionImport":
            self.ts_import()
        elif act_name == "actionExport":
            self.ts_export()
        elif act_name == "actionExport_All":
            self.ts_export_all()
        elif act_name == "actionRemove":
            self.ts_remove()

    def cb_menu_tools(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionShow_size":
            self.sizes_hidden = not action.isChecked()
            self.tree_stories.setColumnHidden(COL_SIZE, self.sizes_hidden)

            # # do we need to compute sizes ?
            if not self.sizes_hidden:
                self.worker_launch(ACTION_SIZE)
            else:
                self.app.postEvent(self.tree_stories, QtCore.QEvent(QtCore.QEvent.Resize))

        elif act_name == "actionShow_story_details":
            self.details_hidden = not action.isChecked()

            selection = self.tree_stories.selectedItems()
            show_details = len(selection) == 1 and not self.details_hidden
            self.te_story_details.setVisible(show_details)
            self.lbl_picture.setVisible(show_details)

        elif act_name == "actionShow_Log":
            main_geometry = self.geometry()
            debug_geometry = self.debug_dialog.geometry()

            # computing log geometry
            child_x = main_geometry.x() + main_geometry.width() + 5
            child_y = main_geometry.y()
            child_width = debug_geometry.width()
            child_height = main_geometry.height()

            # apply new geo
            self.debug_dialog.setGeometry(child_x, child_y, child_width, child_height)
            self.debug_dialog.show()

        elif act_name == "actionGet_firmware":
            # prompt for Luniistore connection
            if self.login_dialog.exec_() != QDialog.Accepted:
                return
            login, password = self.login_dialog.get_login_password()

            try:
                # getting auth token
                auth_token = lunii_get_authtoken(login, password)
                if not auth_token:
                    self.sb_update(f"⚠️ Login failed, please check your credentials")
                    return

                self.sb_update(f"Login success...")
                version = lunii_fw_version(self.audio_device.device_version, auth_token)

                if version:
                    backup_fw_fn = f"fa.v{version}.bin"
                else:
                    backup_fw_fn = f"fa.v3.bin"
                print(backup_fw_fn)

                options = QFileDialog.Options()
                file_dialog = QFileDialog(self, options=options)
                file_dialog.setAcceptMode(QFileDialog.AcceptSave)
                file_dialog.setNameFilter("Lunii Firmware (*.bin);;All Files (*)")

                # Preconfigure a default name
                file_dialog.selectFile(backup_fw_fn)

                if file_dialog.exec_() == QFileDialog.Accepted:
                    selected_file = file_dialog.selectedFiles()[0]
                    if lunii_fw_download(self.audio_device.device_version, self.audio_device.snu_str, auth_token, selected_file):
                        self.sb_update(f"✅ Firmware downloaded to {os.path.basename(selected_file)}")
                    else:
                        self.sb_update(f"🛑 Fail to download update")
                else:
                    self.sb_update("")
                    return

                if self.audio_device.device_version == LUNII_V1:
                    version = lunii_fw_version(self.audio_device.device_version, auth_token, True)
                    backup_fw_fn = f"fu.v{version}.bin"

                    options = QFileDialog.Options()
                    file_dialog = QFileDialog(self, options=options)
                    file_dialog.setAcceptMode(QFileDialog.AcceptSave)
                    file_dialog.setNameFilter("Lunii Firmware (*.bin);;All Files (*)")

                    # Preconfigure a default name
                    file_dialog.selectFile(backup_fw_fn)

                    if file_dialog.exec_() == QFileDialog.Accepted:
                        selected_file = file_dialog.selectedFiles()[0]
                        if lunii_fw_download(self.audio_device.device_version, self.audio_device.snu_str, auth_token, selected_file, True):
                            self.sb_update(f"✅ Firmware downloaded to {os.path.basename(selected_file)}")
                        else:
                            self.sb_update(f"🛑 Fail to download update")
            except requests.exceptions.ConnectionError:
                self.sb_update(f"🛑 Network error...")

    def cb_menu_help(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionAbout":
            about_dlg()
        elif act_name == "actionUpdate":
            website_url = QUrl('https://github.com/o-daneel/Lunii.QT/releases/latest')
            # Open the URL in the default web browser
            QDesktopServices.openUrl(website_url)

    def cb_menu_story_update(self):
        # all disabled
        for action in self.menuStory.actions():
            action.setEnabled(False)

        # during download or no device selected, no action possible
        if not self.audio_device or self.worker:
            return

        # always possible to import in an empty device
        self.act_import.setEnabled(True)

        # pointing to an item
        if self.tree_stories.selectedItems():
            self.act_mv_top.setEnabled(True)
            self.act_mv_up.setEnabled(True)
            self.act_mv_down.setEnabled(True)
            self.act_mv_bottom.setEnabled(True)
            self.act_remove.setEnabled(True)

            # v3 without keys cannot export
            if (self.audio_device.device_version == FLAM_V1 or
                self.audio_device.device_version < LUNII_V3 or
                    (self.audio_device.device_version == LUNII_V3 and self.audio_device.device_key)):
                self.act_export.setEnabled(True)

            # Official story export is forbidden
            if not constants.REFRESH_CACHE:
                selected = self.tree_stories.selectedItems()
                if len(selected) == 1:
                    one_story = self.audio_device.stories.get_story(selected[0].text(COL_UUID))
                    if one_story.is_official():
                        self.act_export.setEnabled(False)

        # are there story loaded ?
        if self.audio_device.stories:
            if (self.audio_device.device_version < LUNII_V3 or
                    (self.audio_device.device_version == LUNII_V3 and self.audio_device.device_key)):
                self.act_exportall.setEnabled(True)

    def cb_menu_tools_update(self):
        self.act_getfw.setEnabled(False)

        if self.audio_device:
            self.act_getfw.setEnabled(True)

    def cb_menu_help_update(self):
        if self.last_version and self.last_version != APP_VERSION:
            self.menuHelp.setTitle("[ Help ]")
            self.menuUpdate.setTitle("New update is available")
            self.act_update.setText(f"Update to {self.last_version}")
            self.act_update.setVisible(True)
        else:
            self.act_update.setVisible(False)

    def ts_update(self):
        # clear previous story list
        self.tree_stories.clear()
        self.ts_populate()
        # update status in status bar
        # self.sb_update_summary()

    def ts_populate(self):
        # empty device
        if not self.audio_device or not self.audio_device.stories or len(self.audio_device.stories) == 0:
            return

        # creating font
        console_font = QFont()
        console_font.setFamilies([u"Consolas"])

        # getting filter text
        le_filter = self.le_filter.text()

        # adding items
        for story in self.audio_device.stories:
            # filtering 
            if le_filter and not le_filter.lower() in story.name.lower():
                continue

            # create and add item to treeWidget
            item = QTreeWidgetItem()
            item.setText(COL_NAME, story.name)
            if story.is_official():
                item.setText(COL_DB, "O")
            else:
                item.setText(COL_DB, "T")
            item.setTextAlignment(COL_DB, Qt.AlignCenter)
            item.setText(COL_UUID, story.str_uuid)
            item.setFont(COL_UUID, console_font)
            if story.size != -1:
                item.setText(COL_SIZE, f"{round(story.size/1024/1024, 1)}MB")
            item.setTextAlignment(COL_SIZE, Qt.AlignRight)
            self.tree_stories.addTopLevelItem(item)

    def sb_create(self):
        self.statusBar().showMessage("bla-bla bla")
        self.lbl_hsnu = QLabel("SNU:")
        self.lbl_snu = QLabel()
        self.lbl_version = QLabel()
        self.lbl_hfs = QLabel("Free :")
        self.lbl_fs = QLabel()
        self.lbl_count = QLabel()
        self.lbl_hsnu.setStyleSheet('border: 0; color:  grey;')
        self.lbl_snu.setStyleSheet('border: 0; color:  grey;')
        self.lbl_version.setStyleSheet('border: 0; color:  grey;')
        self.lbl_hfs.setStyleSheet('border: 0; color:  grey;')
        self.lbl_fs.setStyleSheet('border: 0; color:  grey;')
        self.lbl_count.setStyleSheet('border: 0; color:  grey;')

        self.statusBar().reformat()
        self.statusBar().setStyleSheet('border: 0; background-color: #FFF8DC;')
        self.statusBar().setStyleSheet("QStatusBar::item {border: none;}")

        self.statusBar().addPermanentWidget(VLine())    # <---
        self.statusBar().addPermanentWidget(self.lbl_hsnu)
        self.statusBar().addPermanentWidget(self.lbl_snu)
        self.statusBar().addPermanentWidget(VLine())    # <---
        self.statusBar().addPermanentWidget(self.lbl_version)
        self.statusBar().addPermanentWidget(VLine())    # <---
        self.statusBar().addPermanentWidget(self.lbl_hfs)
        self.statusBar().addPermanentWidget(self.lbl_fs)
        self.statusBar().addPermanentWidget(VLine())    # <---
        self.statusBar().addPermanentWidget(self.lbl_count)

        # self.lbl_snu.setText("2302303012345")
        # self.lbl_fs.setText("1234 MB")

    def sb_update(self, message):
        self.lbl_snu.setText("")
        self.lbl_version.setText("")
        self.lbl_fs.setText("")
        self.lbl_count.setText("")
        self.statusbar.showMessage(message)
        if message:
            self.logger.log(logging.INFO, message)

        if not self.audio_device:
            return

        # SNU
        self.lbl_snu.setText(self.audio_device.snu_str)
        # self.lbl_snu.setText("23023030012345")

        # Version
        version = ""
        if self.audio_device.device_version == LUNII_V1:
            HW_version = "Lunii v1"
            SW_version = f"{self.audio_device.fw_vers_major}.{self.audio_device.fw_vers_minor}"
        elif self.audio_device.device_version == LUNII_V2:
            HW_version = "Lunii v2"
            SW_version = f"{self.audio_device.fw_vers_major}.{self.audio_device.fw_vers_minor}"
        elif self.audio_device.device_version == LUNII_V3:
            HW_version = "Lunii v3"
            SW_version = f"{self.audio_device.fw_vers_major}.{self.audio_device.fw_vers_minor}.{self.audio_device.fw_vers_subminor}"
        elif self.audio_device.device_version == FLAM_V1:
            HW_version = "Flam v1"
            SW_version = f"v{self.audio_device.fw_main}"
        else:
            HW_version = "?v1/v2?"
            SW_version = f"{self.audio_device.fw_vers_major}.{self.audio_device.fw_vers_minor}"
        self.lbl_version.setText(f"{HW_version}, FW: {SW_version}")

        # Free Space
        free_space = psutil.disk_usage(str(self.audio_device.mount_point)).free
        free_space = free_space//1024//1024
        self.lbl_fs.setText(f"{free_space} MB")

        color = "grey"
        if free_space < 500:
            color = "red"
        self.lbl_hfs.setStyleSheet(f'border: 0; color:  {color};')
        self.lbl_fs.setStyleSheet(f'border: 0; color:  {color};')

        # Story count
        count_items = self.tree_stories.topLevelItemCount()
        if count_items:
            self.lbl_count.setText(f"{count_items} stories")
        else:
            self.lbl_count.setText("")

    def ts_move(self, offset):
        if self.worker or not self.audio_device:
            return

        # start = time.time()

        # shifting to be right is shifting to the left the reverse list
        if offset >= 1:
            self.audio_device.stories.reverse()

        working_list = [[story, index+1] for index, story in enumerate(self.audio_device.stories)]

        # getting selection
        selected_items = self.tree_stories.selectedItems()
        if len(selected_items) == 0:
            return
        items_to_move = [item.text(COL_UUID) for item in selected_items]

        # computing new index for each item in working_list
        prev_index = -1
        first_index = -1
        for list_index, s_tuple in enumerate(working_list):
            # current item is to be moved
            if s_tuple[0].str_uuid in items_to_move:
                # if not already on top of list
                if prev_index != -1:
                    # move top / bottom requested ?
                    if abs(offset) > 1:
                        ref = working_list[first_index][1]
                    else:
                        ref = working_list[prev_index][1]
                    # updating its new index
                    working_list[list_index][1] = ref - ref / working_list[list_index][1]
            else:
                # this element is not moved, to be kept as the next to be used for shifting
                prev_index = list_index

                # first value moved
                if first_index == -1:
                    first_index = prev_index

        # sorting item based on new index
        working_list.sort(key= lambda x: x[1])

        # updating story list
        self.audio_device.stories = StoryList()
        for story, index in working_list:
            self.audio_device.stories.append(story)

        # we shifted the reverse list, we need to reverse it one last time
        if offset >= 1:
            self.audio_device.stories.reverse()

        # # update Lunii device (.pi)
        self.audio_device.update_pack_index()

        # refresh stories
        self.ts_update()

        # update selection
        sel_model = self.tree_stories.selectionModel()

        # selecting moved items
        moved = None
        for index in range(0, self.tree_stories.topLevelItemCount()):
            item = self.tree_stories.topLevelItem(index)
            if item.text(COL_UUID) in items_to_move:
                # first item moved, need to set selection
                if not moved:
                    self.tree_stories.setCurrentItem(item)
                # keeping last moved
                moved = item
                # selecting the whole line
                for col in [COL_NAME, COL_DB, COL_UUID, COL_SIZE]:
                    sel_model.select(self.tree_stories.indexFromItem(item, col), QItemSelectionModel.Select)

        # end = time.time()
        # print(f"took {end-start:02.3}s")

    def ts_remove(self):
        # getting selection
        selection = self.tree_stories.selectedItems()
        if len(selection) == 0:
            return

        # preparing validation window
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete stories")
        message = "You are requesting to delete : \n"
        for item in selection:
            message += f"- {item.text(COL_NAME)}\n"

        if len(message) > 512:
            message = message[:768] + "..."
            message += "\n(and too many others)\n"

        message += "\nDo you want to proceed ?"
        dlg.setText(message)
        dlg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        dlg.setIcon(QMessageBox.Warning)
        button = dlg.exec_()

        if button != QMessageBox.Ok:
            return

        # processing selection
        to_remove = [item.text(COL_UUID) for item in selection]
        self.worker_launch(ACTION_REMOVE, to_remove)

    def ts_export(self):
        # getting selection
        selection = self.tree_stories.selectedItems()
        if len(selection) == 0:
            return

        out_dir = QFileDialog.getExistingDirectory(self, f"Output Directory for {len(selection)} stories", "",
                                                   QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)

        # if ok pressed
        if out_dir:
            to_export = [item.text(COL_UUID) for item in selection]
            self.worker_launch(ACTION_EXPORT, to_export, out_dir)
        else:
            self.sb_update("🛑 Export cancelled")

    def ts_export_all(self):
        # getting selection
        if self.tree_stories.topLevelItemCount() == 0:
            return

        out_dir = QFileDialog.getExistingDirectory(self, f"Output Directory for {self.tree_stories.topLevelItemCount()} stories", "",
                                                   QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)

        # if ok pressed
        if out_dir:
            to_export = list()
            for index in range(self.tree_stories.topLevelItemCount()):
                item = self.tree_stories.topLevelItem(index)
                to_export.append(item.text(COL_UUID))
            self.worker_launch(ACTION_EXPORT, to_export, out_dir)
        else:
            self.sb_update("🛑 Export All cancelled")

    def ts_import(self):
        if not self.audio_device:
            return

        file_filter = "All supported (*.pk *.7z *.zip);;PK files (*.plain.pk *.pk);;Archive files (*.7z *.zip);;All files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Open Stories", "", file_filter)

        if not files:
            return

        self.worker_launch(ACTION_IMPORT, files)

    def ts_dragenter_action(self, event):
        # a Lunii must be selected
        if not self.audio_device:
            event.ignore()
            return

        # must be files
        if event.mimeData().hasUrls():
            # getting path for dropped files
            file_paths = [url.toLocalFile() for url in event.mimeData().urls()]

            # checking if dropped files are ending with expected extensions
            if (self.audio_device.device_version == FLAM_V1 and
                    all(any(file.endswith(ext) for ext in FLAM_SUPPORTED_EXT) for file in file_paths)):
                event.acceptProposedAction()
            elif all(any(file.endswith(ext) for ext in LUNII_SUPPORTED_EXT) for file in file_paths):
                event.acceptProposedAction()
            else:
                event.ignore()

    def ts_drop_action(self, event):
        # getting path for dropped files
        file_paths = [url.toLocalFile() for url in event.mimeData().urls()]

        self.worker_launch(ACTION_IMPORT, file_paths)

    def worker_launch(self, action, item_list=None, out_dir=None):
        if self.worker:
            return

        if not self.audio_device:
            return

        # setting up the thread
        self.worker = ierWorker(self.audio_device, action, item_list, out_dir)
        self.thread = QtCore.QThread()
        self.worker.moveToThread(self.thread)

        # UI limitations
        self.btn_db.setEnabled(False)
        self.tree_stories.setEnabled(False)

        # connecting slots
        self.thread.started.connect(self.worker.process)
        self.worker.signal_finished.connect(self.slot_finished)
        # self.worker.signal_finished.connect(self.worker.deleteLater)
        # self.thread.finished.connect(self.thread.deleteLater)

        # UI update slots
        self.audio_device.signal_story_progress.connect(self.slot_story_progress)
        self.audio_device.signal_logger.connect(self.logger.log)
        self.worker.signal_total_progress.connect(self.slot_total_progress)
        self.worker.signal_finished.connect(self.thread.quit)
        self.worker.signal_refresh.connect(self.ts_update)
        self.worker.signal_message.connect(self.sb_update)

        # running
        self.thread.start()

    def slot_total_progress(self, current, max_val):
        # updating UI
        self.lbl_total.setVisible(True)
        self.lbl_total.setText(f"Total {current+1}/{max_val}")
        self.pbar_total.setVisible(True)
        self.pbar_total.setRange(0, max_val)
        self.pbar_total.setValue(current+1)

    def slot_story_progress(self, uuid, current, max_val):
        # updating UI
        self.lbl_story.setVisible(True)
        self.lbl_story.setText(uuid)

        self.pbar_story.setVisible(True)
        self.pbar_story.setRange(0, max_val)
        self.pbar_story.setValue(current+1)

    def slot_finished(self):
        # print("SLOT FINISHED")
        # updating UI
        self.tree_stories.setEnabled(True)
        self.btn_db.setEnabled(True)

        self.lbl_total.setVisible(False)
        self.pbar_total.setVisible(False)
        self.lbl_story.setVisible(False)
        self.pbar_story.setVisible(False)

        try:
            self.audio_device.signal_story_progress.disconnect()
        except: pass
        try:
            self.audio_device.signal_logger.disconnect()
        except: pass

        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        if self.thread:
            self.thread.deleteLater()
            self.thread = None

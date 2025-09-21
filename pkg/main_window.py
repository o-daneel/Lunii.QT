import logging
import os.path
import time
from pathlib import WindowsPath

import psutil
import requests
from PySide6 import QtCore, QtGui
from PySide6.QtCore import QItemSelectionModel, QUrl, QSize
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QPixmap, Qt, QDesktopServices, QIcon, QGuiApplication, QColor
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QFileDialog, QMessageBox, QLabel, QFrame, QHeaderView, \
    QDialog, QApplication, QCheckBox

from pkg import versionWorker
from pkg.api import constants
from pkg.api.constants import *
from pkg.api.device_flam import is_flam, FlamDevice
from pkg.api.device_lunii import LuniiDevice, is_lunii
from pkg.api.devices import find_devices
from pkg.api.firmware import luniistore_get_authtoken, device_fw_download, device_fw_getlist
from pkg.api.stories import story_load_db, DESC_NOT_FOUND, StoryList
from pkg.ierWorker import ierWorker, ACTION_REMOVE, ACTION_IMPORT, ACTION_EXPORT, ACTION_SIZE, ACTION_CLEANUP, \
    ACTION_FACTORY, ACTION_RECOVER, ACTION_FIND, ACTION_DB_IMPORT
from pkg.nm_window import NightModeWindow
from pkg.ui.about_ui import about_dlg
from pkg.ui.debug_ui import DebugDialog, LUNII_LOGGER
from pkg.ui.login_ui import LoginDialog
from pkg.ui.main_ui import Ui_MainWindow

COL_NAME = 0
COL_NM = 1
COL_DB = 2
COL_UUID = 3
COL_SIZE = 4

COL_NM_SIZE = 20
COL_DB_SIZE = 20
COL_UUID_SIZE = 250
COL_SIZE_SIZE = 90
COL_EXTRA = 40

APP_VERSION = "v3.0.0a1"

""" 
# TODO : 
- support config to enable / disable night mode
 """

class VLine(QFrame):
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        # internal resources
        self.logger = logging.getLogger(LUNII_LOGGER)

        self.iconLunii = QIcon(":/icon/res/lunii.ico")
        self.iconFlam = QIcon(":/icon/res/flam.ico")
        self.debug_dialog = DebugDialog()
        self.login_dialog = LoginDialog(self)
        self.nm_dialog = NightModeWindow(self)

        # class instance vars init
        self.audio_device: LuniiDevice = None
        self.worker: ierWorker = None
        self.thread: QtCore.QThread = None
        self.version_worker: versionWorker = None
        self.version_thread: QtCore.QThread = None
        self.app = app

        # self.debug_dialog.show() # class instance vars init self.audio_device: LuniiDevice = None self.worker: ierWorker = None self.thread: QtCore.QThread = None self.version_worker: versionWorker = None self.version_thread: QtCore.QThread = None self.app = app # app config
        self.sizes_hidden = True
        self.details_hidden = False
        self.details_last_uuid = None
        self.ffmpeg_present = STORY_TRANSCODING_SUPPORTED

        # actions local storage
        self.act_mv_top = None
        self.act_mv_up = None
        self.act_mv_down = None
        self.act_mv_bottom = None
        self.act_hide = None
        self.act_import = None
        self.act_export = None
        self.act_exportall = None
        self.act_remove = None
        self.act_getfw = None
        self.act_update = None

        # loading DB
        story_load_db(False)

        # UI init
        self.init_ui()

        # refresh devices
        self.cb_device_refresh()

        # starting thread to fetch version
        self.worker_check_version()

    def init_ui(self):
        self.setupUi(self)
        self.modify_widgets()
        self.setup_connections()

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
        self.tree_stories.setColumnWidth(COL_NM, COL_NM_SIZE)
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
        self.btn_abort.setVisible(False)

        # finding menu actions
        s_actions = self.menuStory.actions()
        self.act_mv_top = next(act for act in s_actions if act.objectName() == "actionMove_Top")
        self.act_mv_up = next(act for act in s_actions if act.objectName() == "actionMove_Up")
        self.act_mv_down = next(act for act in s_actions if act.objectName() == "actionMove_Down")
        self.act_mv_bottom = next(act for act in s_actions if act.objectName() == "actionMove_Bottom")
        self.act_hide = next(act for act in s_actions if act.objectName() == "actionHide")
        self.act_nm = next(act for act in s_actions if act.objectName() == "actionNight_Mode")
        self.act_import = next(act for act in s_actions if act.objectName() == "actionImport")
        self.act_export = next(act for act in s_actions if act.objectName() == "actionExport")
        self.act_exportall = next(act for act in s_actions if act.objectName() == "actionExport_All")
        self.act_remove = next(act for act in s_actions if act.objectName() == "actionRemove")

        # Update statusbar
        self.sb_create()

        # Update Menu tools based on config
        t_actions = self.menuTools.actions()
        self.act_getfw = next(act for act in t_actions if act.objectName() == "actionGet_firmware")
        self.act_factory = next(act for act in t_actions if act.objectName() == "actionFactory_reset")
        self.act_factory.setVisible(False)
        act_transcode = next(act for act in t_actions if act.objectName() == "actionTranscode")
        act_transcode.setChecked(self.ffmpeg_present)
        act_transcode.setEnabled(not self.ffmpeg_present)
        act_transcode.setText("FFMPEG detected" if self.ffmpeg_present else "FFMPEG is missing (HowTo 🔗)")

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

        self.btn_refresh.clicked.connect(self.cb_device_refresh)
        self.btn_db.clicked.connect(self.cb_db_refresh)
        self.btn_abort.clicked.connect(self.worker_abort)
        self.btn_nightmode.clicked.connect(self.cb_nm)

        self.tree_stories.itemSelectionChanged.connect(self.cb_tree_select)
        self.tree_stories.installEventFilter(self)

        QApplication.instance().focusChanged.connect(self.onFocusChanged)

        # Connect the context menu
        self.tree_stories.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_stories.customContextMenuRequested.connect(self.cb_show_context_menu)
        # self.tree_stories.itemClicked.connect(self.ts_clicked)

        # connect menu callbacks
        self.menuFile.triggered.connect(self.cb_menu_file)
        self.menuStory.triggered.connect(self.cb_menu_story)
        self.menuStory.aboutToShow.connect(self.cb_menu_story_update)
        self.menuTools.triggered.connect(self.cb_menu_tools)
        self.menuTools.aboutToShow.connect(self.cb_menu_tools_update)
        self.menuLost_stories.triggered.connect(self.cb_menu_lost)
        # self.menuHelp.aboutToShow.connect(self.cb_menu_help_update)
        self.menuHelp.triggered.connect(self.cb_menu_help)

        # story list shortcuts
        QShortcut(QKeySequence("F5"), self, self.cb_device_refresh)
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
                self.tw_resize_columns()
                return True
        return False

    def tw_resize_columns(self):
        # Adjusting cols based on widget size

        # 1. forcing UUID to be at min size by huge name size
        self.tree_stories.setColumnWidth(COL_NAME, 4096)
        # 2. force resize to content
        self.tree_stories.resizeColumnToContents(COL_UUID)
        self.tree_stories.resizeColumnToContents(COL_SIZE)
        # 3. get cur size
        col_uuid_size = self.tree_stories.columnWidth(COL_UUID)
        col_size_size = self.tree_stories.columnWidth(COL_SIZE)

        # 4. update the name col while keeping uuid size
        col_size_width = self.tree_stories.width() - COL_NM_SIZE - COL_DB_SIZE - col_uuid_size
        if not self.sizes_hidden:
            col_size_width -= col_size_size
        col_size_width -= COL_EXTRA
        self.tree_stories.setColumnWidth(COL_NAME, col_size_width)

    def __set_dbg_wndSize(self):
        # Move the sub-window alongside the main window
        main_geometry = self.geometry()
        debug_geometry = self.debug_dialog.geometry()

        debug_geometry.moveTopLeft(main_geometry.topRight() + QtCore.QPoint(5, 0))
        debug_geometry.setHeight(main_geometry.height())

        # getting screen
        screen = QGuiApplication.screenAt(debug_geometry.topLeft())
        if screen:
            screen_geometry = screen.geometry()
            is_inside_screen = screen_geometry.contains(debug_geometry.topLeft() + QtCore.QPoint(100, 0))
        else:
            is_inside_screen = False

        if is_inside_screen:
            self.debug_dialog.setGeometry(debug_geometry)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized() and self.debug_dialog.isVisible():
                # Minimize the log-window when the main window is minimized
                self.debug_dialog.showMinimized()
            elif self.isMaximized() or self.isActiveWindow():
                # restore the log-window when the main window is restored or maximized
                self.debug_dialog.showNormal()
                pass

    def customMoveEvent(self, event):
        # This custom slot is called when the main window is moved
        if self.debug_dialog.isVisible():
            self.__set_dbg_wndSize()

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
        self.hide()

        # waiting for threads to close
        if self.version_thread and self.version_thread.isRunning():
            self.version_thread.wait()
        if self.thread and self.thread.isRunning():
            self.worker_abort()
            self.thread.wait()

        event.accept()

    def cb_show_context_menu(self, point):
        # change active menu based on selection
        self.cb_menu_story_update()

        self.menuStory.exec_(self.tree_stories.mapToGlobal(point))

    def cb_show_log(self):
        # prepare for debug dialog to show
        self.__set_dbg_wndSize()
        # show dialog and give back control to main
        self.debug_dialog.show()
        self.activateWindow()

    # WIDGETS UPDATES
    def cb_dev_add(self, dev_path):
        if is_lunii(dev_path):
            self.combo_device.addItem(self.iconLunii, dev_path)
        elif is_flam(dev_path):
            self.combo_device.addItem(self.iconFlam, dev_path)
        else:
            self.combo_device.addItem(dev_path)

    def cb_device_refresh(self):
        dev_list = find_devices()
        self.combo_device.clear()
        self.audio_device = None

        dev: WindowsPath
        self.combo_device.setPlaceholderText("Select your Lunii")
        self.sb_update("")
        self.chk_nightmode.setEnabled(False)
        self.nm_dialog.remove_audioDevice()


        for dev in dev_list:
            dev_name = str(dev)
            # print(dev_name)
            self.cb_dev_add(dev_name)

        self.setWindowIcon(self.iconLunii)
        if self.combo_device.count():
            self.combo_device.setPlaceholderText("Select your Lunii")

            # automatic select if only one device
            if self.combo_device.count() == 1:
                self.setWindowIcon(self.combo_device.itemIcon(0))
                self.combo_device.setCurrentIndex(0)

        else:
            self.sb_update("No Lunii detected 😥, try File/Open")
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
                self.worker.abort_process = True
                while self.worker:
                    self.app.processEvents()
                    time.sleep(0.05)

            # update app icon based on cb item
            self.setWindowIcon(self.combo_device.itemIcon(self.combo_device.currentIndex()))

            # open device
            try:
                if is_lunii(dev_name):
                    self.audio_device = LuniiDevice(dev_name, V3_KEYS)
                else:
                    self.audio_device = FlamDevice(dev_name)
            except PermissionError:
                error = "🛑 PermissionError : Unable to open this device"
                self.logger.log(logging.ERROR, error)
                self.statusbar.showMessage(error)
                return

            self.statusbar.showMessage(f"")

            # widgets update with new device
            self.ts_update()
            self.tw_resize_columns()
            self.sb_update("")

            if self.audio_device.device_version != FLAM_V1:
                self.btn_nightmode.setEnabled(True)
                self.cb_nm_update_btn()

            # night mode section
            self.chk_nightmode.setEnabled(True)
            self.chk_nightmode.setChecked(self.audio_device.config[LUNII_CFGPOS_NM_ENABLED] == 1)
            self.nm_dialog.set_audioDevice(self.audio_device)

            # computing sizes if necessary
            if not self.sizes_hidden and any(story for story in self.audio_device.stories if story.size == -1):
                self.worker_launch(ACTION_SIZE)
            
            # showLog window if device is a v3 without story keys
            if (self.audio_device and
                self.audio_device.device_version == LUNII_V3 and
                not self.audio_device.story_key):
                self.cb_show_log()

    def cb_tree_select(self):
        # getting selection
        selection = self.tree_stories.selectedItems()
        show_details = len(selection) == 1 and not self.details_hidden
        self.te_story_details.setVisible(show_details)
        self.lbl_picture.setVisible(show_details)

        if show_details:
            item = selection[0]
            uuid = item.text(COL_UUID)

            # update selection to show cursor if hidden by UI
            self.tree_stories.scrollToItem(item)

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

            # hidden story
            self.te_story_details.setDisabled(one_story.hidden)
            self.lbl_picture.setDisabled(one_story.hidden)

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
        self.pbar_total.setRange(0, 100)
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

    def cb_lbl_click(self, event):
        if self.audio_device:
            msg = str(self.audio_device)
            self.logger.log(logging.INFO, msg)
            self.statusbar.showMessage("Device info sent to clipboard.")
            clipboard = QApplication.clipboard()
            clipboard.setText(msg)

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
            if not is_lunii(dev_dir) and not is_flam(dev_dir):
                self.sb_update("Not a Lunii, nor Flam or unsupported one 😥")
                return

            # add device to list
            device_list = [self.combo_device.itemText(i) for i in range(self.combo_device.count())]
            if dev_dir not in device_list:
                self.cb_dev_add(dev_dir)
                index = self.combo_device.findText(dev_dir)
                self.combo_device.setCurrentIndex(index)
        elif act_name == "actionImport_DB":
            file_filter = "STUdio DB (unofficial.json);;All DBs (*.json);;All files (*)"
            STUDIO_DIR: Path = os.path.join(Path.home(), ".studio/db")
            file, _ = QFileDialog.getOpenFileName(self, "Open STUdio DB", STUDIO_DIR, file_filter)
            if not file:
                return

            self.worker_launch(ACTION_DB_IMPORT, file)

        elif act_name == "actionRefresh_DB":
            self.cb_db_refresh()

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
        elif act_name == "actionHide":
            self.ts_hide()
        elif act_name == "actionNight_Mode":
            self.ts_nm()
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
            # already visible ? so hide it
            if self.debug_dialog.isVisible():
                self.debug_dialog.hide()
                return

            # not visible, prepare location to show it
            if not self.isMaximized():
                self.cb_show_log()              # prepare log size, show and activate
            else:
                self.debug_dialog.show()        # show me debug log wnd

        elif act_name == "actionGet_firmware":
            # prompt for Luniistore connection
            if self.login_dialog.exec_() != QDialog.Accepted:
                return
            login, password = self.login_dialog.get_login_password()

            try:
                # getting auth token
                auth_token = luniistore_get_authtoken(login, password)
                if not auth_token:
                    self.sb_update(f"⚠️ Login failed, please check your credentials")
                    return
                self.sb_update(f"Login success...")

                # getting list of FW to download
                fw_list = device_fw_getlist(self.audio_device.device_version, self.audio_device.snu_str, auth_token)

                # preparing save dialog
                options = QFileDialog.Options()
                file_dialog = QFileDialog(self, directory=CFG_DIR, options=options)
                file_dialog.setAcceptMode(QFileDialog.AcceptSave)
                if self.audio_device.device_version == FLAM_V1:
                    file_dialog.setNameFilter("Flam Firmware (*.enc);;All Files (*)")
                else:
                    file_dialog.setNameFilter("Lunii Firmware (*.bin);;All Files (*)")

                # looping to download all of them
                for index, one_fw in enumerate(fw_list):
                    # Preconfigure a default name
                    file_dialog.selectFile(one_fw)

                    if file_dialog.exec_() == QFileDialog.Accepted:
                        selected_file = file_dialog.selectedFiles()[0]
                        if device_fw_download(self.audio_device.device_version, self.audio_device.snu_str, auth_token,
                                              selected_file, index != 0):
                            self.sb_update(f"✅ Firmware downloaded to {os.path.basename(selected_file)}")
                        else:
                            self.sb_update(f"🛑 Fail to download update")
                    else:
                        self.sb_update("")
                        return

            except requests.exceptions.ConnectionError:
                self.sb_update(f"🛑 Network error...")

        elif act_name == "actionTranscode":
            website_url = QUrl('https://github.com/o-daneel/Lunii.QT?tab=readme-ov-file#audio-transcoding')
            # Open the URL in the default web browser
            QDesktopServices.openUrl(website_url)

        elif act_name == "actionFactory_reset":
            # TODO request confirmation before performing

            # starting reset process
            self.worker_launch(ACTION_FACTORY)

    def cb_menu_lost(self, action: QtGui.QAction):
        # prepare for debug dialog to show
        self.__set_dbg_wndSize()
        self.debug_dialog.show()
        self.activateWindow()

        # handling action
        act_name = action.objectName()
        if act_name == "actionFind_stories":
            self.worker_launch(ACTION_FIND)
        elif act_name == "actionRecover_stories":
            self.worker_launch(ACTION_RECOVER)
        elif act_name == "actionRemove_stories":
            self.worker_launch(ACTION_CLEANUP)

    def cb_menu_help(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionAbout":
            about_dlg(self)
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
        # except if not story keys are present for v3
        if (self.audio_device.device_version == LUNII_V3 and not self.audio_device.story_key):
            self.act_import.setEnabled(False)   

        # pointing to an item
        if self.tree_stories.selectedItems():
            self.act_mv_top.setEnabled(True)
            self.act_mv_up.setEnabled(True)
            self.act_mv_down.setEnabled(True)
            self.act_mv_bottom.setEnabled(True)
            self.act_hide.setEnabled(True)
            self.act_nm.setEnabled(True)
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
            if (self.audio_device.device_version == FLAM_V1 or
                    self.audio_device.device_version < LUNII_V3 or
                    (self.audio_device.device_version == LUNII_V3 and self.audio_device.device_key)):
                self.act_exportall.setEnabled(True)

    def cb_menu_tools_update(self):
        device_selected: bool = self.audio_device is not None

        self.act_getfw.setEnabled(device_selected)
        self.act_factory.setEnabled(False)
        self.menuLost_stories.setEnabled(device_selected)

    def cb_menu_help_update(self, last_version):
        if last_version:
            self.logger.log(logging.INFO, f"Latest Github release {last_version}")
        else:
            self.logger.log(logging.WARN, f"🛑 Unable to fetch version from Github")

        # hidden by default
        self.act_update.setVisible(False)

        # if a version was fetched
        if last_version:
            new_update = False

            c_versions = APP_VERSION.split("a")
            l_versions = last_version.split("a")

            c_alpha = len(c_versions) > 1
            l_alpha = len(l_versions) > 1

            # none of them are alpha (stable vs stable) : 2.7.8 2.7.9
            # stable vs aplha : 2.7.8 2.7.9a1
            # alpha vs stable : 2.7.9a1 2.7.9
            # alpha vs alpha  : 2.7.9a1 2.7.9a2
            new_update = (l_versions[0] > c_versions[0]) or \
                (c_alpha and l_alpha and l_versions[1] > c_versions[1]) or \
                (l_versions[0] == c_versions[0] and c_alpha and not l_alpha)

            if new_update:
                self.menuHelp.setTitle("[ Help ]")
                self.menuUpdate.setTitle("New update is available")
                self.act_update.setText(f"Update to {last_version}")
                self.act_update.setVisible(True)

    def ts_update(self):
        # clear previous story list
        self.tree_stories.clear()
        self.details_last_uuid = None
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
            if (le_filter and
                not le_filter.lower() in story.name.lower() and
                not le_filter.lower() in story.str_uuid.lower() ):
                continue

            # create and add item to treeWidget
            item = QTreeWidgetItem()

            item.setText(COL_NAME, story.name)
            item.setText(COL_NM, "🛏️" if story.night_mode() else "")
            item.setTextAlignment(COL_NM, Qt.AlignCenter)

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

            if story.hidden:
                grey_color = QColor(128, 128, 128)
                for column in range(item.columnCount()):
                    item.setToolTip(column, "Story is hidden for LuniiStore synchronization")
                    item.setForeground(column, grey_color)

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

        # Create the checkbox
        self.chk_nightmode = QCheckBox("Night Mode", self)
        self.chk_nightmode.setChecked(False)
        self.chk_nightmode.setEnabled(False)
        self.chk_nightmode.stateChanged.connect(self.cbnm_checked)

        self.statusBar().addPermanentWidget(self.chk_nightmode)
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

        self.lbl_snu.setToolTip(str(self.audio_device))
        self.lbl_version.setToolTip(str(self.audio_device))
        self.lbl_snu.mousePressEvent = self.cb_lbl_click
        self.lbl_version.mousePressEvent = self.cb_lbl_click

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
    
    def cb_nm(self):
        result = self.nm_dialog.exec()

        if result == QDialog.Accepted:
            print("Validate, update conf")
            old_config = self.audio_device.config 
            new_config = self.nm_dialog.config
            print(old_config)
            print(new_config)
            self.audio_device.config = self.nm_dialog.config
            self.audio_device.update_config()

            # updating button image
            self.cb_nm_update_btn()

    def cb_nm_update_btn(self):
        icon_nm = QIcon()
        if self.audio_device.device_version != FLAM_V1 and self.audio_device.config[LUNII_CFGPOS_NM_ENABLED] == 1:
            icon_nm.addFile(u":/icon/res/mode_night.png", QSize(), QIcon.Normal, QIcon.Off)
        else:
            icon_nm.addFile(u":/icon/res/mode_day.png", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_nightmode.setIcon(icon_nm)


    def cbnm_checked(self, state):
        if not self.audio_device:
            return

        night_mode = self.chk_nightmode.isChecked()
        self.audio_device.config[LUNII_CFGPOS_NM_ENABLED] = 1 if night_mode else 0
        self.audio_device.update_config()
    
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
        working_list.sort(key=lambda x: x[1])

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
                for col in [COL_NAME, COL_NM, COL_DB, COL_UUID, COL_SIZE]:
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

    def ts_hide(self):
        if not self.audio_device:
            return

        # getting selection
        selection = self.tree_stories.selectedItems()
        if len(selection) == 0:
            return

        # updating story hidden state
        items_to_hide = []
        one_story = None
        for item in selection:
            one_story = self.audio_device.stories.get_story(item.text(COL_UUID))
            one_story.hidden = not one_story.hidden
            items_to_hide.append(self.tree_stories.indexOfTopLevelItem(item))

        # updating pack index file and display
        self.audio_device.update_pack_index()
        self.ts_update()

        # update selection
        sel_model = self.tree_stories.selectionModel()

        # selecting moved items
        new_selection = [self.tree_stories.topLevelItem(index) for index in items_to_hide]
        self.tree_stories.setCurrentItem(new_selection[0])
        for item in new_selection:
            for col in [COL_NAME, COL_NM, COL_DB, COL_UUID, COL_SIZE]:
                sel_model.select(self.tree_stories.indexFromItem(item, col), QItemSelectionModel.Select)

        # updating detail panel
        self.te_story_details.setDisabled(one_story.hidden)
        self.lbl_picture.setDisabled(one_story.hidden)

        self.sb_update("✅ Stories updated...")

    def ts_nm(self):
        if not self.audio_device:
            return

        # getting selection
        selection = self.tree_stories.selectedItems()
        if len(selection) == 0:
            return

        # updating story nightmode state
        items_to_toggle = []
        one_story = None
        for item in selection:
            one_story = self.audio_device.stories.get_story(item.text(COL_UUID))
            one_story.nm = not one_story.nm
            # managing nm file for stories
            story_nm = os.path.join(self.audio_device.story_dir(one_story.short_uuid), "nm")
            # if nm file exists
            if os.path.isfile(story_nm):
                # remove it
                os.remove(story_nm)
            else:
                # create empty nm file
                open(story_nm, 'w').close()

            # keeping track of TreeView items for selection management
            items_to_toggle.append(self.tree_stories.indexOfTopLevelItem(item))


        self.ts_update()

        # update selection
        sel_model = self.tree_stories.selectionModel()

        # selecting moved items
        new_selection = [self.tree_stories.topLevelItem(index) for index in items_to_toggle]
        self.tree_stories.setCurrentItem(new_selection[0])
        for item in new_selection:
            for col in [COL_NAME, COL_NM, COL_DB, COL_UUID, COL_SIZE]:
                sel_model.select(self.tree_stories.indexFromItem(item, col), QItemSelectionModel.Select)

        self.sb_update("✅ Stories updated...")

    def ts_import(self):
        if not self.audio_device:
            return

        if self.audio_device.device_version == FLAM_V1:
            file_filter = "All supported (*.7z *.zip);;All files (*)"
        else:
            file_filter = "All supported (*.pk *.7z *.zip);;PK files (*.plain.pk *.pk);;Archive files (*.7z *.zip);;All files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Open Stories", "", file_filter)

        if not files:
            return

        self.sb_update("Importing stories...")
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
            if self.audio_device.device_version == FLAM_V1:
                # for flam
                if all(any(file.endswith(ext) for ext in FLAM_SUPPORTED_EXT) for file in file_paths):
                    event.acceptProposedAction()
                    return
            else:
                # for lunii
                if all(any(file.endswith(ext) for ext in LUNII_SUPPORTED_EXT) for file in file_paths):
                    event.acceptProposedAction()
                    return

            event.ignore()

    def ts_drop_action(self, event):
        if (self.audio_device.device_version == LUNII_V3 and not self.audio_device.story_key):
            self.sb_update("🛑 Unable to import story, missing story key for Lunii v3")
            return
        
        # getting path for dropped files
        file_paths = [url.toLocalFile() for url in event.mimeData().urls()]

        self.sb_update("Importing stories...")
        self.worker_launch(ACTION_IMPORT, file_paths)

    def ts_clicked(self, item, column):
        if column == COL_NM:
            self.ts_nm()

    def worker_check_version(self):
        # version_thread.start()
        self.version_worker = versionWorker.VersionChecker()
        self.version_thread = QtCore.QThread()

        self.version_worker.update_available.connect(self.cb_menu_help_update)
        self.version_thread.started.connect(self.version_worker.check_for_updates)

        # move worker to the worker thread
        self.version_worker.moveToThread(self.version_thread)

        # start the thread
        self.version_thread.start()

    def worker_launch(self, action, item_list=None, out_dir=None):
        if self.worker:
            return

        # if not self.audio_device:
        #     return

        # setting up the thread
        self.worker = ierWorker(self.audio_device, action, item_list, out_dir, not self.sizes_hidden and action == ACTION_IMPORT)
        self.thread = QtCore.QThread()
        self.worker.moveToThread(self.thread)

        # UI limitations
        self.btn_db.setEnabled(False)
        self.tree_stories.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.combo_device.setEnabled(False)

        # connecting slots
        self.thread.started.connect(self.worker.process)
        self.worker.signal_finished.connect(self.slot_finished)
        # self.worker.signal_finished.connect(self.worker.deleteLater)
        # self.thread.finished.connect(self.thread.deleteLater)

        # UI update slots
        if self.audio_device:
            self.audio_device.signal_story_progress.connect(self.slot_story_progress)
            self.audio_device.signal_logger.connect(self.logger.log)
        self.worker.signal_total_progress.connect(self.slot_total_progress)
        self.worker.signal_finished.connect(self.thread.quit)
        self.worker.signal_refresh.connect(self.ts_update)
        self.worker.signal_message.connect(self.sb_update)
        self.worker.signal_showlog.connect(self.cb_show_log)

        # running
        self.thread.start()

    def worker_abort(self):
        if not self.worker:
            return

        # pushing message
        self.sb_update("Abort requested, please wait...")

        # trying to abort current process
        self.worker.abort_process = True
        self.audio_device.abort_process = True

    def slot_total_progress(self, current, max_val):
        # updating UI
        self.lbl_total.setVisible(True)
        self.lbl_total.setText(f"Total {current+1}/{max_val}")
        self.pbar_total.setVisible(True)
        self.pbar_total.setRange(0, max_val)
        self.pbar_total.setValue(current+1)

        self.btn_abort.setVisible(True)

    def slot_story_progress(self, uuid, current, max_val):
        # updating UI
        self.lbl_story.setVisible(True)
        self.lbl_story.setText(uuid)

        self.pbar_story.setVisible(True)
        self.pbar_story.setRange(0, max_val)
        self.pbar_story.setValue(current+1)

        self.btn_abort.setVisible(True)

    def slot_finished(self):
        # print("SLOT FINISHED")
        # updating UI
        self.tree_stories.setEnabled(True)
        self.btn_db.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.combo_device.setEnabled(True)

        # hiding progress
        self.lbl_total.setVisible(False)
        self.pbar_total.setVisible(False)
        self.lbl_story.setVisible(False)
        self.pbar_story.setVisible(False)
        self.btn_abort.setVisible(False)

        try:
            self.audio_device.signal_story_progress.disconnect()
        except:
            pass
        try:
            self.audio_device.signal_logger.disconnect()
        except:
            pass

        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        if self.thread:
            self.thread.deleteLater()
            self.thread = None

import datetime
import logging
import re
import time
from pathlib import WindowsPath
import uuid
import json

import psutil
import requests

from PySide6 import QtCore, QtGui
from PySide6.QtCore import QItemSelectionModel, QUrl, QSize, QTimer, QModelIndex, QSortFilterProxyModel, QEvent
from PySide6.QtGui import QFont, QShortcut, QKeySequence, Qt, QDesktopServices, QIcon, QGuiApplication, QColor, QImage, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QFileDialog, QMessageBox, QLabel, QFrame, QHeaderView, \
    QDialog, QApplication, QListView, QAbstractItemView, QStyledItemDelegate

from pkg import versionWorker
from pkg.api import constants
from pkg.api import stories
from pkg.api.constants import *
from pkg.api.device_flam import is_flam, FlamDevice
from pkg.api.device_lunii import LuniiDevice, is_lunii
from pkg.api.devices import find_devices
from pkg.api.firmware import luniistore_get_authtoken, device_fw_download, device_fw_getlist
from pkg.api.stories import AGE_NOT_FOUND, DB_LOCAL_LIBRARY_COL_AGE, DB_LOCAL_LIBRARY_COL_NAME, DB_LOCAL_LIBRARY_COL_PATH, story_load_db, StoryList
from pkg.audio_player import AudioPlayer
from pkg.icons import SimpleLazyLoadingModel, FixedSizeDelegate, create_image_stack_base64
from pkg.ierWorker import ierWorker, ACTION_REMOVE, ACTION_IMPORT, ACTION_EXPORT, ACTION_SIZE, ACTION_CLEANUP, \
    ACTION_FACTORY, ACTION_RECOVER, ACTION_FIND, ACTION_DB_IMPORT, ACTION_IMPORT_IN_LIBRAIRY
from pkg.nm_window import NightModeWindow
from pkg.settings import Settings
from pkg.ui.about_ui import about_dlg
from pkg.ui.debug_ui import DebugDialog, LUNII_LOGGER
from pkg.ui.login_ui import LoginDialog
from pkg.ui.main_ui import Ui_MainWindow

COL_NAME = 0
COL_NM = 1
COL_DB = 2
COL_UUID = 3
COL_SIZE = 4

COL_OFFICIAL_AGE = 0
COL_OFFICIAL_NAME = 1
COL_OFFICIAL_LANGUAGE = 2
COL_OFFICIAL_INSTALLED = 3
COL_OFFICIAL_PATH = 4
COL_OFFICIAL_UUID = 5
COL_OFFICIAL_SIZE = 6

COL_THIRD_PARTY_AGE = 0
COL_THIRD_PARTY_NAME = 1
COL_THIRD_PARTY_INSTALLED = 2
COL_THIRD_PARTY_PATH = 3
COL_THIRD_PARTY_UUID = 4
COL_THIRD_PARTY_SIZE = 5

COL_NM_SIZE = 20
COL_DB_SIZE = 20
COL_UUID_SIZE = 250
COL_NAME_MIN_SIZE = 510
COL_SIZE_SIZE = 90
COL_EXTRA = 40
PREVIEW_MIN_SIZE = 256

APP_VERSION = "v3.1.2"

"""
# TODO :
 """

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.settings = Settings(FILE_SETTINGS)
        self.audio_player = AudioPlayer()

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
        self.ffmpeg_present = STORY_TRANSCODING_SUPPORTED

        # initialize settings
        if self.settings.sizes_hidden is None:
            self.settings.sizes_hidden = True
        if self.settings.show_gallery is None:
            self.settings.show_gallery = False
        if self.settings.show_unavailable_stories is None:
            self.settings.show_unavailable_stories = True
        if self.settings.displayed_languages is None:
            self.settings.displayed_languages = []
        if self.settings.current_tab_index is None:
            self.settings.current_tab_index = 0
        if self.settings.main_window_is_maximized is None:
            self.settings.main_window_is_maximized = False
        if self.settings.auto_play is None:
            self.settings.auto_play = False

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
        self.act_import_in_library = None
        self.act_auto_play = None
        self.act_save_pack = None
        self.act_load_pack = None

        # loading DB
        story_load_db(False)

        # UI init
        self.init_ui()

        # Restore UI based on settings
        if self.settings.main_window_is_maximized:
            self.showMaximized()

        QTimer.singleShot(0, self.load_initial_content)

    def init_ui(self):
        self.setupUi(self)
        self.modify_widgets()
        self.setup_connections()

    def load_initial_content(self):
        self.lock_ui()
        self.sb_update(self.tr("⌛ Checking for updates, please wait..."))
        self.worker_check_version()
        self.sb_update(self.tr("⌛ Loading devices, please wait..."))
        self.cb_device_refresh()
        self.sb_update(self.tr("⌛ Loading catalogs' content, please wait..."))
        self.ts_update()
        self.sb_update("" if self.audio_device is None else self.tr("No Lunii detected 😥, try File/Open"))

        # Populate language filter
        filtered_languages = self.settings.displayed_languages
        for lang in sorted({list(stories.DB_OFFICIAL[id]["locales_available"].keys())[0] for id in stories.DB_OFFICIAL}):
            combo_item = QStandardItem(lang)
            combo_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            combo_item.setData(Qt.Checked if lang in filtered_languages else Qt.Unchecked, Qt.CheckStateRole)
            self.combo_language_filter.model().appendRow(combo_item)
        self.combo_language_update_text()

        for min_age in sorted({stories.DB_OFFICIAL[id].get("age_min") for id in stories.DB_OFFICIAL}):
            if min_age == -1:
                continue
            self.combo_age_min_filter.addItem(str(min_age))
            self.combo_age_max_filter.addItem(str(min_age))

        if self.settings.filtered_min_age:
            self.combo_age_min_filter.setCurrentText(self.settings.filtered_min_age)
        if self.settings.filtered_max_age:
            self.combo_age_max_filter.setCurrentText(self.settings.filtered_max_age)
        
        self.unlock_ui()


    # update ui elements state (enable, disable, context enu)
    def modify_widgets(self):
        title = f"Lunii Qt-Manager {APP_VERSION}"
        self.setWindowTitle(title)
        self.logger.log(logging.INFO, title)

        self.menuUpdate.setVisible(False)
        self.menuUpdate.setTitle("")

        # self.pgb_total.setVisible(False)
        self.combo_language_filter.setModel(QStandardItemModel())
        self.combo_language_filter.setView(QListView())

        self.tabWidget.setCurrentIndex(self.settings.current_tab_index)

        # QTreeWidget for stories
        self.tree_stories.clear()
        self.tree_stories.setColumnWidth(COL_NAME, COL_NAME_MIN_SIZE)
        self.tree_stories.header().setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        self.tree_stories.header().setSectionResizeMode(COL_DB, QHeaderView.Fixed)
        self.tree_stories.header().setSectionResizeMode(COL_NM, QHeaderView.Fixed)
        self.tree_stories.header().setSectionResizeMode(COL_UUID, QHeaderView.Fixed)
        self.tree_stories.header().setSectionResizeMode(COL_SIZE, QHeaderView.Fixed)
        self.tree_stories.setColumnWidth(COL_UUID, COL_UUID_SIZE)
        self.tree_stories.setColumnWidth(COL_NM, COL_NM_SIZE)
        self.tree_stories.setColumnWidth(COL_DB, COL_DB_SIZE)
        self.tree_stories.setColumnHidden(COL_SIZE, self.settings.sizes_hidden)
        self.tree_stories.setVisible(not self.settings.show_gallery)

        self.splitter.setSizes([COL_NAME_MIN_SIZE + COL_UUID_SIZE + COL_NM_SIZE + COL_DB_SIZE, PREVIEW_MIN_SIZE])

        self.tree_stories_official.setColumnWidth(COL_OFFICIAL_UUID, COL_UUID_SIZE)
        self.tree_stories_official.setColumnWidth(COL_OFFICIAL_NAME, COL_NAME_MIN_SIZE)
        self.tree_stories_official.header().setSectionResizeMode(COL_OFFICIAL_NAME, QHeaderView.Stretch)
        self.tree_stories_official.header().setSectionResizeMode(COL_OFFICIAL_AGE, QHeaderView.ResizeToContents)
        self.tree_stories_official.header().setSectionResizeMode(COL_OFFICIAL_PATH, QHeaderView.Stretch)
        self.tree_stories_official.header().setSectionResizeMode(COL_OFFICIAL_LANGUAGE, QHeaderView.ResizeToContents)
        self.tree_stories_official.header().setSectionResizeMode(COL_OFFICIAL_INSTALLED, QHeaderView.ResizeToContents)
        self.tree_stories_official.header().setSectionResizeMode(COL_OFFICIAL_UUID, QHeaderView.Fixed)
        self.tree_stories_official.header().setSectionResizeMode(COL_OFFICIAL_SIZE, QHeaderView.ResizeToContents)
        self.tree_stories_official.sortItems(COL_OFFICIAL_AGE, QtCore.Qt.AscendingOrder)
        self.tree_stories_official.setVisible(not self.settings.show_gallery)

        self.tree_stories_third_party.setColumnWidth(COL_THIRD_PARTY_UUID, COL_UUID_SIZE)
        self.tree_stories_third_party.setColumnWidth(COL_THIRD_PARTY_NAME, COL_NAME_MIN_SIZE)
        self.tree_stories_third_party.header().setSectionResizeMode(COL_THIRD_PARTY_NAME, QHeaderView.Stretch)
        self.tree_stories_third_party.header().setSectionResizeMode(COL_THIRD_PARTY_AGE, QHeaderView.ResizeToContents)
        self.tree_stories_third_party.header().setSectionResizeMode(COL_THIRD_PARTY_PATH, QHeaderView.Stretch)
        self.tree_stories_third_party.header().setSectionResizeMode(COL_THIRD_PARTY_INSTALLED, QHeaderView.ResizeToContents)
        self.tree_stories_third_party.header().setSectionResizeMode(COL_THIRD_PARTY_UUID, QHeaderView.Fixed)
        self.tree_stories_third_party.header().setSectionResizeMode(COL_THIRD_PARTY_SIZE, QHeaderView.ResizeToContents)
        self.tree_stories_third_party.sortItems(COL_THIRD_PARTY_NAME, QtCore.Qt.AscendingOrder)
        self.tree_stories_third_party.setItemDelegate(ColumnEditableDelegate(editable_columns={COL_THIRD_PARTY_AGE, COL_THIRD_PARTY_NAME}))
        self.tree_stories_third_party.setVisible(not self.settings.show_gallery)

        self.list_stories.setViewMode(QListView.IconMode)
        self.list_stories.setIconSize(QSize(300, 300))
        self.list_stories.setGridSize(QSize(320, 360))
        self.list_stories.setResizeMode(QListView.Adjust)
        self.list_stories.setDragEnabled(False)
        self.list_stories.setAcceptDrops(False)
        self.list_stories.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.list_stories.setVisible(self.settings.show_gallery)
        self.list_stories_official.setViewMode(QListView.IconMode)
        self.list_stories_official.setIconSize(QSize(300, 300))
        self.list_stories_official.setGridSize(QSize(320, 360))
        self.list_stories_official.setResizeMode(QListView.Adjust)
        self.list_stories_official.setDragEnabled(False)
        self.list_stories_official.setAcceptDrops(False)
        self.list_stories_official.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.list_stories_official.setVisible(self.settings.show_gallery)
        self.list_stories_third_party.setViewMode(QListView.IconMode)
        self.list_stories_third_party.setIconSize(QSize(300, 300))
        self.list_stories_third_party.setGridSize(QSize(320, 360))
        self.list_stories_third_party.setResizeMode(QListView.Adjust)
        self.list_stories_third_party.setDragEnabled(False)
        self.list_stories_third_party.setAcceptDrops(False)
        self.list_stories_third_party.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.list_stories_third_party.setVisible(self.settings.show_gallery)

        self.story_details.setOpenLinks(False)
        self.story_details.setOpenExternalLinks(True)
        self.story_details.anchorClicked.connect(self.cb_story_details_open_links)

        # clean progress bars
        self.lbl_total.setVisible(False)
        self.pbar_total.setVisible(False)
        self.lbl_story.setVisible(False)
        self.pbar_story.setVisible(False)
        self.pbar_file.setVisible(False)
        self.btn_abort.setVisible(False)

        # audio buttons
        self.audio_button_previous.setVisible(self.settings.auto_play)
        self.audio_button_stop.setVisible(self.settings.auto_play)
        self.audio_button_play.setVisible(self.settings.auto_play)
        self.audio_button_pause.setVisible(self.settings.auto_play)
        self.audio_button_next.setVisible(self.settings.auto_play)

        # Update statusbar
        self.sb_create()

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
        self.act_save_pack = next(act for act in s_actions if act.objectName() == "actionSavePack")
        self.act_load_pack = next(act for act in s_actions if act.objectName() == "actionLoadPack")
        self.act_auto_play = next(act for act in s_actions if act.objectName() == "actionAutoPlay")
        self.act_auto_play.setChecked(self.settings.auto_play)

        l_actions = self.menuLibrary.actions()
        self.act_import_in_library = next(act for act in l_actions if act.objectName() == "actionImportInLibrary")
        act_gallery = next(act for act in l_actions if act.objectName() == "actionShow_gallery")
        act_gallery.setChecked(self.settings.show_gallery)
        act_show_unavailable_stories = next(act for act in l_actions if act.objectName() == "actionShow_unavailable_stories")
        act_show_unavailable_stories.setChecked(self.settings.show_unavailable_stories)

        # Update Menu tools based on config
        t_actions = self.menuTools.actions()
        self.act_getfw = next(act for act in t_actions if act.objectName() == "actionGet_firmware")
        self.act_factory = next(act for act in t_actions if act.objectName() == "actionFactory_reset")
        self.act_factory.setVisible(False)
        act_transcode = next(act for act in t_actions if act.objectName() == "actionTranscode")
        act_transcode.setChecked(self.ffmpeg_present)
        act_transcode.setEnabled(not self.ffmpeg_present)
        act_transcode.setText("FFMPEG detected" if self.ffmpeg_present else "FFMPEG is missing (HowTo 🔗)")

        act_size = next(act for act in t_actions if act.objectName() == "actionShow_size")
        act_size.setChecked(not self.settings.sizes_hidden)

        # Help Menu
        t_actions = self.menuHelp.actions()
        self.act_update = next(act for act in t_actions if act.objectName() == "actionUpdate")
        self.act_update.setVisible(False)

        # Connect the main window's moveEvent to the custom slot
        self.moveEvent = self.customMoveEvent

        # Setup splitter priority
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        if self.settings.main_window_splitter_position is not None:
            self.splitter.setSizes(self.settings.main_window_splitter_position)

    # connecting slots and signals
    def setup_connections(self):
        self.tabWidget.currentChanged.connect(self.cb_tab_changed)
        self.combo_device.currentIndexChanged.connect(self.cb_dev_select)
        self.combo_age_min_filter.currentIndexChanged.connect(self.cb_combo_min_age_changed)
        self.combo_age_max_filter.currentIndexChanged.connect(self.cb_combo_max_age_changed)

        self.combo_language_filter.model().itemChanged.connect(self.cb_combo_language_changed)
        self.combo_language_filter.view().pressed.connect(self.cb_combo_language_pressed)

        # Adding delay to avoid refreshing on each filter's letters
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(300)
        self.le_filter.textChanged.connect(self.cb_filter_text_changed)
        self.filter_timer.timeout.connect(self.ts_update)

        self.btn_refresh.clicked.connect(self.cb_device_refresh)
        self.btn_db.clicked.connect(self.cb_db_refresh)
        self.btn_abort.clicked.connect(self.worker_abort)
        self.btn_nightmode.clicked.connect(self.cb_nm)

        self.audio_button_previous.clicked.connect(self.audio_player.play_previous)
        self.audio_button_stop.clicked.connect(self.audio_player.stop)
        self.audio_button_play.clicked.connect(self.audio_player.play)
        self.audio_button_pause.clicked.connect(self.audio_player.pause)
        self.audio_button_next.clicked.connect(self.audio_player.play_next)

        self.splitter_timer = QTimer()
        self.splitter_timer.setSingleShot(True)
        self.splitter_timer.timeout.connect(self.cb_splitter_released)
        self.splitter.splitterMoved.connect(self.cb_splitter_moved)
        self.splitter.splitterMoved.connect(self.cb_story_select)
        self.tree_stories.selectionModel().selectionChanged.connect(self.cb_story_select)
        self.tree_stories_official.selectionModel().selectionChanged.connect(self.cb_story_select)
        self.tree_stories_third_party.selectionModel().selectionChanged.connect(self.cb_story_select)

        self.tree_stories.installEventFilter(self)
        self.tree_stories_official.installEventFilter(self)
        self.tree_stories_third_party.installEventFilter(self)

        self.tree_stories_third_party.itemChanged.connect(self.cb_item_changed)

        self.tree_stories_official.itemDoubleClicked.connect(self.cb_install_or_remove_story_on_lunii)
        self.list_stories_official.doubleClicked.connect(self.cb_install_or_remove_story_on_lunii)
        self.tree_stories_third_party.doubleClicked.connect(self.cb_install_or_remove_story_on_lunii)
        self.list_stories_third_party.doubleClicked.connect(self.cb_install_or_remove_story_on_lunii)

        self.add_story_button.clicked.connect(self.cb_install_or_remove_story_on_lunii)
        self.remove_story_button.clicked.connect(self.cb_install_or_remove_story_on_lunii)

        QApplication.instance().focusChanged.connect(self.onFocusChanged)

        # Connect the context menu
        self.tree_stories.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_stories.customContextMenuRequested.connect(self.cb_show_context_menu)
        self.list_stories.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list_stories.customContextMenuRequested.connect(self.cb_show_context_menu)
        # self.tree_stories.itemClicked.connect(self.ts_clicked)

        # connect menu callbacks
        self.menuFile.triggered.connect(self.cb_menu_file)
        self.menuStory.triggered.connect(self.cb_menu_story)
        self.menuStory.aboutToShow.connect(self.cb_menu_story_update)
        self.menuLibrary.triggered.connect(self.cb_menu_library)
        self.menuLibrary.aboutToShow.connect(self.cb_menu_library_update)
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
                self.cb_story_select()
                return False
        elif obj.objectName() == "tree_stories_official":
            if event.type() == QtCore.QEvent.Resize:
                self.cb_story_select()
                return False
        elif obj.objectName() == "tree_stories_third_party":
            if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Delete and (event.modifiers() & Qt.ShiftModifier):
                item = self.tree_stories_third_party.currentItem()
                if not item:
                    return False
                reply = QMessageBox.question(self.tree_stories_third_party, "Confirm", f"Delete entry '{item.text(COL_THIRD_PARTY_NAME)}' ?", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    stories.local_library_db_delete(item.text(COL_THIRD_PARTY_UUID))
                    stories.thirdparty_db_del_story(uuid.UUID(item.text(COL_THIRD_PARTY_UUID)))
                    index = self.tree_stories_third_party.indexOfTopLevelItem(item)
                    self.tree_stories_third_party.setCurrentItem(self.tree_stories_third_party.topLevelItem(max(0, index - 1)))
                    self.tree_stories_third_party.takeTopLevelItem(index)

                    self.story_details.setText("")

                return True
            elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_F2:
                item = self.tree_stories_third_party.currentItem()
                if item:
                    self.tree_stories_third_party.edit(self.tree_stories_third_party.indexFromItem(item, COL_THIRD_PARTY_NAME))
                    return True

            elif event.type() == QtCore.QEvent.Resize:
                self.cb_story_select()
                return False

        return False

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
    
            if self.isVisible():
                self.settings.main_window_is_maximized = self.isMaximized()

            if not self.debug_dialog.isVisible():
                return

            if self.isMinimized():
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

    def cb_story_details_open_links(self, url: QUrl):
        QDesktopServices.openUrl(url)

    def cb_splitter_moved(self):
        # start a timer to avoid saving settings too much
        self.splitter_timer.start(1000)

    def cb_splitter_released(self):
        self.settings.main_window_splitter_position = self.splitter.sizes()

    def cb_combo_min_age_changed(self):
        self.settings.filtered_min_age = self.combo_age_min_filter.currentText()
        self.ts_update()
        
    def cb_combo_max_age_changed(self):
        self.settings.filtered_max_age = self.combo_age_max_filter.currentText()
        self.ts_update()

    def cb_combo_language_pressed(self, index):
        model = self.combo_language_filter.model()
        item = model.itemFromIndex(index)
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
        self.cb_combo_language_changed(item)

    def cb_combo_language_changed(self, item):
        if item.checkState() == Qt.Checked:
            if item.text() not in self.settings.displayed_languages:
                self.settings.displayed_languages.append(item.text())
        elif item.text() in self.settings.displayed_languages:
            self.settings.displayed_languages.remove(item.text())
        
        self.combo_language_update_text()
        QTimer.singleShot(0, self.ts_update)

    def combo_language_update_text(self):
        if len(self.settings.displayed_languages) == 0:
            self.combo_language_filter.setPlaceholderText(self.tr("Filter Language..."))
        elif len(self.settings.displayed_languages) > 2:
            self.combo_language_filter.setPlaceholderText((", ".join(self.settings.displayed_languages[:2]) + "..."))
        else:
            self.combo_language_filter.setPlaceholderText(", ".join(self.settings.displayed_languages))

    def cb_item_changed(self, item, column):
        age = item.text(COL_THIRD_PARTY_AGE)
        name = item.text(COL_THIRD_PARTY_NAME)
        uuid = item.text(COL_THIRD_PARTY_UUID)

        stories.local_library_db_add_or_update(uuid, age= age, name= name)

    def cb_tab_changed(self):
        self.settings.current_tab_index = self.tabWidget.currentIndex()
        self.cb_story_select()
        self.combo_language_filter.setEnabled(self.tabWidget.currentIndex() == 1)
        self.combo_age_min_filter.setEnabled(self.tabWidget.currentIndex() != 0)
        self.combo_age_max_filter.setEnabled(self.tabWidget.currentIndex() != 0)

    def cb_show_context_menu(self, point):
        # change active menu based on selection
        self.cb_menu_story_update()

        if self.settings.show_gallery:
            self.menuStory.exec_(self.list_stories.mapToGlobal(point))
        else:
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
        self.combo_device.setPlaceholderText(self.tr("Select your Lunii"))
        self.sb_update("")
        self.nm_dialog.remove_audioDevice()

        if os.path.isdir("lunii-sd/"):
            print("Adding fake Flam from lunii-sd")
            dev_list.append("lunii-sd/_flam_fake/")
        
        for dev in dev_list:
            dev_name = str(dev)
            # print(dev_name)
            self.cb_dev_add(dev_name)

        self.setWindowIcon(self.iconLunii)
        if self.combo_device.count():
            self.combo_device.setPlaceholderText(self.tr("Select your Lunii"))

            # automatic select if only one device
            if self.combo_device.count() == 1:
                self.setWindowIcon(self.combo_device.itemIcon(0))
                self.combo_device.setCurrentIndex(0)

        else:
            self.sb_update(self.tr("No Lunii detected 😥, try File/Open"))
            self.combo_device.setPlaceholderText(self.tr("No Lunii detected 😥"))
            self.act_load_pack.setEnabled(False)


    def cb_dev_select(self):
        # cleanup
        self.audio_device = None
        self.nm_dialog.remove_audioDevice()
        # updating UI for default
        self.btn_nightmode.setEnabled(False)
        self.cb_nm_update_btn()
        self.act_load_pack.setEnabled(True)

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
                    check_refresh_cache(self.audio_device.snu)
                else:
                    self.audio_device = FlamDevice(dev_name)
            except PermissionError:
                error = self.tr("🛑 PermissionError : Unable to open this device")
                self.logger.log(logging.ERROR, error)
                self.statusbar.showMessage(error)
                return

            self.statusbar.showMessage(f"")

            # widgets update with new device
            self.ts_update()
            self.sb_update("")

            # night mode section
            if self.audio_device.device_version != FLAM_V1:
                self.nm_dialog.set_audioDevice(self.audio_device)
                self.btn_nightmode.setEnabled(True)
                self.cb_nm_update_btn()
                self.tree_stories.setColumnHidden(COL_NM, False)
            else:
                self.tree_stories.setColumnHidden(COL_NM, True)

            # computing sizes if necessary
            if not self.settings.sizes_hidden and any(story for story in self.audio_device.stories if story.size == -1):
                self.worker_launch(ACTION_SIZE)

            # showLog window if device is a v3 without story keys
            if (self.audio_device and
                self.audio_device.device_version == LUNII_V3 and
                not self.audio_device.story_key):
                self.cb_show_log()

    def cb_install_or_remove_story_on_lunii(self):
        if not self.audio_device:
            return

        to_remove_ids = []
        to_remove_names = []
        if self.tabWidget.currentIndex() == 0 and not self.settings.show_gallery:
            multiple_selection = self.get_multiple_selection()
            if len(multiple_selection) > 1:
                for (id, name) in multiple_selection:
                    to_remove_ids.append(id if self.audio_device is FlamDevice else self.audio_device.stories.get_story(id).short_uuid)
                    to_remove_names.append(name)
            else:
                (id, local_db_path, lunii_story_id, name) = self.get_single_selection()
                if id is not None:
                    to_remove_ids.append(self.audio_device.stories.get_story(id).uuid if self.audio_device is FlamDevice else self.audio_device.stories.get_story(id).short_uuid)
                    to_remove_names.append(name)
        else:
            (id, local_db_path, lunii_story_id, name) = self.get_single_selection()

            if lunii_story_id != "" and local_db_path != "":
                to_remove_ids.append(lunii_story_id)
                to_remove_names.append(name)
            elif local_db_path != "":
                self.sb_update(self.tr(f'Importing story "{name}" from "{local_db_path}"...'))
                self.worker_launch(ACTION_IMPORT, [local_db_path])

        if len(to_remove_ids) > 0:
            self.audio_player.stop(True)
            self.sb_update(self.tr(f'Removing stories "{to_remove_names}"...'))
            self.worker_launch(ACTION_REMOVE, to_remove_ids)
        return

    def cb_story_select(self):
        # Add asynchronous system to handle the delay on the UI
        QTimer.singleShot(0, self.process_story_select)

    def check_image_in_cache(self, uuid: str):
        if not os.path.isfile(os.path.join(CACHE_DIR, uuid)):
            stories.get_picture(uuid)

    def get_single_selection(self):
        if self.settings.show_gallery:
            return self.get_single_selection_from_listviews()
        else:
            return self.get_single_selection_from_treeview()

    def get_single_selection_from_treeview(self):
        if self.tabWidget.currentIndex() == 0:
            selection = self.tree_stories.selectedItems()
        elif self.tabWidget.currentIndex() == 1:
            selection = self.tree_stories_official.selectedItems()
        elif self.tabWidget.currentIndex() == 2:
            selection = self.tree_stories_third_party.selectedItems()
            
        if selection is not None and len(selection) == 1:
            item = selection[0]

            if self.tabWidget.currentIndex() == 0:
                id = item.text(COL_UUID)
                local_db_path = ""
                lunii_story_id = ""
                name = item.text(COL_NAME)

            elif self.tabWidget.currentIndex() == 1:
                id = item.text(COL_OFFICIAL_UUID)
                local_db_path = item.text(COL_OFFICIAL_PATH)
                lunii_story_id = item.text(COL_OFFICIAL_INSTALLED)
                name = item.text(COL_OFFICIAL_NAME)

            elif self.tabWidget.currentIndex() == 2:
                id = item.text(COL_THIRD_PARTY_UUID)
                local_db_path = item.text(COL_THIRD_PARTY_PATH)
                lunii_story_id = item.text(COL_THIRD_PARTY_INSTALLED)
                name = item.text(COL_THIRD_PARTY_NAME)

            return (id, local_db_path, lunii_story_id, name)

        return (None, None, None, None)

    def get_single_selection_from_listviews(self):
        if self.tabWidget.currentIndex() == 0:
            selection = self.list_stories.selectionModel().selectedRows()
        elif self.tabWidget.currentIndex() == 1:
            selection = self.list_stories_official.selectionModel().selectedRows()
        elif self.tabWidget.currentIndex() == 2:
            selection = self.list_stories_third_party.selectionModel().selectedRows()
        
        if len(selection) == 1:
            data = selection[0].data(Qt.UserRole)
            id = data["id"]
            local_db_path = data["local_db_path"]
            lunii_story_id = data["lunii_story_id"]
            name = data["name"]

            return (id, local_db_path, lunii_story_id, name)
        
        return (None, None, None, None)

    def get_multiple_selection(self):
        result = []
        if not self.settings.show_gallery:
            for item in self.tree_stories.selectedItems():
                result.append((item.text(COL_UUID), item.text(COL_NAME)))
        else:
            for row in self.list_stories.selectionModel().selectedRows():
                data = row.data(Qt.UserRole)
                result.append((data["id"], data["name"]))

        return result

    def process_story_select(self):
        self.add_story_button.setEnabled(False)
        self.remove_story_button.setEnabled(False)
        self.act_save_pack.setEnabled(False)

        if self.tabWidget.currentIndex() == 0:
            multiple_selection = self.get_multiple_selection()
            if len(multiple_selection) > 1:
                paths = []
                names = []
                for (id, name) in multiple_selection:
                    self.check_image_in_cache(id)
                    one_story = self.audio_device.stories.get_story(id)
                    age = "" if not one_story or one_story.age == AGE_NOT_FOUND else str(one_story.age) + "+ "
                    paths.append(os.path.join(CACHE_DIR, id))
                    names.append(age + name)

                data_uri = create_image_stack_base64(paths, min(self.story_details.width() - 20, 512))
                html = "" if data_uri is None else f'<img src="{data_uri}" style="max-width:100%; height:auto;" />'

                for name in names:
                    html += f"<BR/><b>{name}</b>"
                self.story_details.setHtml(html)
                self.act_save_pack.setEnabled(True)
                return
    
            (id, local_db_path, lunii_story_id, name) = self.get_single_selection()
            
            self.remove_story_button.setEnabled(True)
            one_story = self.audio_device.stories.get_story(id)
            if not one_story:
                self.story_details.setHtml("")
                return
            
            self.check_image_in_cache(id)
            url = os.path.join(CACHE_DIR, id)
            width = min(self.story_details.width() - 20, QImage(url).width())
            age = "" if one_story.age == AGE_NOT_FOUND else str(one_story.age) + "+ "
            self.story_details.setHtml(
                f'<img src="{url}" width="{width}" />'
                + f"<h2>{age}{name}</h2>"
                + f"<h3>{one_story.subtitle}</h3>"
                + f"<h4>{one_story.author}</h4>"
                + one_story.desc)
            
            if self.settings.auto_play:
                self.audio_player.play_story_from_device(self.audio_device, self.audio_device.story_dir(one_story))

        elif self.tabWidget.currentIndex() == 1:
            (id, local_db_path, lunii_story_id, name) = self.get_single_selection()

            self.add_story_button.setEnabled(self.audio_device is not None and local_db_path != "" and lunii_story_id == "")
            self.remove_story_button.setEnabled(self.audio_device is not None and lunii_story_id != "")

            if id is not None:
                self.check_image_in_cache(id)

                locale = list(stories.DB_OFFICIAL[id]["locales_available"].keys())[0]
                description = stories.DB_OFFICIAL[id]["localized_infos"][locale].get("description", "")
                title = stories.DB_OFFICIAL[id]["localized_infos"][locale].get("title", "")
                subtitle = stories.DB_OFFICIAL[id]["localized_infos"][locale].get("subtitle", "")
                url = os.path.join(CACHE_DIR, id)
                width = min(self.story_details.width() - 20, QImage(url).width())
                age = f'{stories.DB_OFFICIAL[id]["age_min"]}+ '
                creation_date = datetime.datetime.fromtimestamp(stories.DB_OFFICIAL[id].get("creation_date") / 1000)
                modification_date = datetime.datetime.fromtimestamp(stories.DB_OFFICIAL[id].get("creation_date") / 1000)
                duration = int(stories.DB_OFFICIAL[id].get("duration")) / 1000

                dates_tag = f'<br><br>Ajouté en {creation_date.strftime("%B %Y")}'
                if modification_date != creation_date:
                    dates_tag += f'<br>Modifié en {modification_date.strftime("%B %Y")}'
                dates_tag += f'<br>Durée {int(duration // 3600)}h {(int(duration % 3600) // 60)}min'

                if local_db_path != "":
                    path_tag = f'<br><br><a href="{QUrl.fromLocalFile(os.path.dirname(local_db_path)).toString()}">{os.path.dirname(local_db_path)}</a>' \
                        + f' - <a href="{QUrl.fromLocalFile(local_db_path).toString()}">{os.path.basename(local_db_path)}</a>' \
                        + f' - {round(os.path.getsize(local_db_path)/1024/1024, 1)}MB' 
                
                    if self.settings.auto_play:
                        self.audio_player.play_story_from_archive(local_db_path)
                else:
                    path_tag = ""

                    if self.settings.auto_play:
                        self.audio_player.play_audio_from_list([OFFICIAL_DB_RESOURCES_URL + preview for preview in stories.DB_OFFICIAL[id].get("previews", [])])
                    
                self.story_details.setHtml(
                    f'<img src="{url}" width="{width}" /><br>'
                    + f"<h2>{age}{title}</h2>"
                    + f'<h3>{subtitle}</h3>'
                    + description + path_tag + dates_tag)

        elif self.tabWidget.currentIndex() == 2:
            (id, local_db_path, lunii_story_id, name) = self.get_single_selection()

            self.add_story_button.setEnabled(self.audio_device is not None and local_db_path != "" and lunii_story_id == "")
            self.remove_story_button.setEnabled(self.audio_device is not None and lunii_story_id != "")

            if id is not None and id in stories.DB_THIRD_PARTY:
                self.check_image_in_cache(id)
                description = stories.DB_THIRD_PARTY[id].get("description", "")
                url = os.path.join(CACHE_DIR, id)
                img_tag = "" if not os.path.isfile(url) else f'<img src="{url}" width="{min(self.story_details.width() - 20, QImage(url).width())}" /><br>'
                title_tag = f'<h2>{name}</h2>'
                desc_tag = "" if description is None else description
                if local_db_path != "":
                    path_tag = f'<br><br><a href="{QUrl.fromLocalFile(os.path.dirname(local_db_path)).toString()}">{os.path.dirname(local_db_path)}</a>' \
                        + f' - <a href="{QUrl.fromLocalFile(local_db_path).toString()}">{os.path.basename(local_db_path)}</a>' \
                        + f' - {round(os.path.getsize(local_db_path)/1024/1024, 1)}MB' 
                
                    if self.settings.auto_play:
                        self.audio_player.play_story_from_archive(local_db_path)
                else:
                    path_tag = ""

                self.story_details.setHtml(img_tag + title_tag + desc_tag + path_tag)
            else:
                self.story_details.setText("")

    def cb_db_refresh(self):
        self.sb_update(self.tr("Fetching official Lunii DB..."))
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
            self.sb_update(self.tr("👍 Lunii DB refreshed."))
        else:
            self.sb_update(self.tr("🛑 Lunii DB failed."))

    def cb_lbl_click(self, event):
        if self.audio_device:
            msg = str(self.audio_device)
            self.logger.log(logging.INFO, msg)
            self.statusbar.showMessage(self.tr("Device info sent to clipboard."))
            clipboard = QApplication.clipboard()
            clipboard.setText(msg)

    def cb_menu_file(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionOpen_Lunii":

            # file_filter = "Lunii Metadata (.md);;All files (*)"
            # file, _ = QFileDialog.getOpenFileName(self, "Open Lunii device", "", file_filter)
            dev_dir = QFileDialog.getExistingDirectory(self, self.tr("Open Lunii device"), "",
                                                       QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
            if not dev_dir:
                return

            # check if path is a recognized device
            if not is_lunii(dev_dir) and not is_flam(dev_dir):
                self.sb_update(self.tr("Not a Lunii, nor Flam or unsupported one 😥"))
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
            file, _ = QFileDialog.getOpenFileName(self, self.tr("Open STUdio DB"), STUDIO_DIR, file_filter)
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
        elif act_name == "actionAutoPlay":
            self.settings.auto_play = self.act_auto_play.isChecked()
            self.audio_button_previous.setVisible(self.settings.auto_play)
            self.audio_button_stop.setVisible(self.settings.auto_play)
            self.audio_button_play.setVisible(self.settings.auto_play)
            self.audio_button_pause.setVisible(self.settings.auto_play)
            self.audio_button_next.setVisible(self.settings.auto_play)
            if not self.settings.auto_play:
                self.audio_player.stop()

            self.cb_story_select()
        elif act_name == "actionSavePack":
            self.ts_save_pack()
        elif act_name == "actionLoadPack":
            self.ts_load_pack()

    def cb_menu_library(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionShow_gallery":
            self.settings.show_gallery = action.isChecked()
            self.tree_stories.setVisible(not self.settings.show_gallery)
            self.list_stories.setVisible(self.settings.show_gallery)
            self.tree_stories_official.setVisible(not self.settings.show_gallery)
            self.list_stories_official.setVisible(self.settings.show_gallery)
            self.tree_stories_third_party.setVisible(not self.settings.show_gallery)
            self.list_stories_third_party.setVisible(self.settings.show_gallery)
            self.story_details.setText("")

        elif act_name == "actionImportInLibrary":
            self.ts_import_in_library()
        elif act_name == "actionShow_unavailable_stories":
            self.lock_ui()
            self.settings.show_unavailable_stories = action.isChecked()
            self.ts_update()
            self.unlock_ui()

    def cb_menu_tools(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionShow_size":
            self.settings.sizes_hidden = not action.isChecked()
            self.tree_stories.setColumnHidden(COL_SIZE, self.settings.sizes_hidden)

            # # do we need to compute sizes ?
            if not self.settings.sizes_hidden:
                # update sizes only if a device is selected
                if self.audio_device:
                    self.worker_launch(ACTION_SIZE)
            else:
                self.app.postEvent(self.tree_stories, QtCore.QEvent(QtCore.QEvent.Resize))

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
                    self.sb_update(self.tr("⚠️ Login failed, please check your credentials"))
                    return
                self.sb_update(self.tr("Login success..."))

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
                            dld = self.tr("✅ Firmware downloaded to")
                            self.sb_update(dld + f" {os.path.basename(selected_file)}")
                        else:
                            self.sb_update(self.tr("🛑 Fail to download update"))
                    else:
                        self.sb_update("")
                        return

            except requests.exceptions.ConnectionError:
                self.sb_update(self.tr("🛑 Network error..."))

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
            if action.objectName() != "actionAutoPlay" and action.objectName() != "actionSavePack" and action.objectName() != "actionLoadPack":
                action.setEnabled(False)

        # during download or no device selected, no action possible
        if not self.audio_device or self.worker:
            return

        # always possible to import in an empty device
        self.act_import.setEnabled(True)

        # except if not story keys are present for v3
        if self.audio_device.device_version == LUNII_V3 and not self.audio_device.story_key:
            self.act_import.setEnabled(False)

        selected = None
        if self.settings.show_gallery:
            if len(self.list_stories.selectionModel().selectedRows()) > 0:
                self.act_mv_top.setEnabled(True)
                self.act_mv_up.setEnabled(True)
                self.act_mv_down.setEnabled(True)
                self.act_mv_bottom.setEnabled(True)
                self.act_remove.setEnabled(True)
                self.act_export.setEnabled(True)
        elif self.tree_stories.selectedItems():
            self.act_mv_top.setEnabled(True)
            self.act_mv_up.setEnabled(True)
            self.act_mv_down.setEnabled(True)
            self.act_mv_bottom.setEnabled(True)
            self.act_hide.setEnabled(True)
            self.act_nm.setEnabled(True)
            self.act_remove.setEnabled(True)
            self.act_export.setEnabled(True)

            # Official story export is forbidden for Luniis (no piracy on Flam)
            if self.audio_device.device_version < LUNII_V3:
                selected = self.tree_stories.selectedItems()
                if len(selected) == 1 and not constants.REFRESH_CACHE:
                    one_story = self.audio_device.stories.get_story(selected[0].text(COL_UUID))
                    if one_story.is_official():
                        self.act_export.setEnabled(False)


        # pointing to an item
        if selected:
            self.act_mv_top.setEnabled(True)
            self.act_mv_up.setEnabled(True)
            self.act_mv_down.setEnabled(True)
            self.act_mv_bottom.setEnabled(True)
            self.act_hide.setEnabled(True)
            self.act_nm.setEnabled(True)
            self.act_remove.setEnabled(True)
            self.act_export.setEnabled(True)

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

    def cb_menu_library_update(self):
        device_selected: bool = self.audio_device is not None

        self.act_getfw.setEnabled(device_selected)
        self.act_factory.setEnabled(False)
        self.menuLost_stories.setEnabled(device_selected)

    def cb_menu_help_update(self, last_version):
        if last_version:
            self.logger.log(logging.INFO, self.tr("Latest Github release") + f" {last_version}")
        else:
            self.logger.log(logging.WARN, self.tr("🛑 Unable to fetch version from Github"))

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
                self.menuHelp.setTitle(self.tr("[ Help ]"))
                self.menuUpdate.setTitle(self.tr("Update is available"))
                self.act_update.setText(self.tr("Update to {}").format(last_version))
                self.act_update.setVisible(True)

    def cb_filter_text_changed(self):
        self.filter_timer.start()

    def ts_update(self):
        # clear previous story list
        self.tree_stories.clear()
        self.tree_stories_official.clear()
        self.tree_stories_third_party.clear()

        if self.list_stories.model() is not None:
            self.list_stories.model().clear()       
        if self.list_stories_official.model() is not None:
            self.list_stories_official.model().sourceModel().clear()
        if self.list_stories_third_party.model() is not None:
            self.list_stories_third_party.model().sourceModel().clear()

        self.ts_populate()
        self.ts_populate_official()
        self.ts_populate_third_party()

        if self.list_stories.selectionModel() is not None:
            self.list_stories.selectionModel().currentChanged.connect(self.cb_story_select)
        self.list_stories_official.selectionModel().currentChanged.connect(self.cb_story_select)
        self.list_stories_third_party.selectionModel().currentChanged.connect(self.cb_story_select)

        self.cb_story_select()

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
        data_list = []
        for story in self.audio_device.stories:
            local_story = None if story.str_uuid not in stories.DB_LOCAL_LIBRARY else stories.DB_LOCAL_LIBRARY[story.str_uuid]
            display_name = story.name if local_story is None or not DB_LOCAL_LIBRARY_COL_NAME in local_story else local_story[DB_LOCAL_LIBRARY_COL_NAME]
            # filtering
            if (le_filter and
                not le_filter.lower() in display_name.lower() and
                not le_filter.lower() in story.str_uuid.lower() ):
                continue

            # create and add item to treeWidget
            item = QTreeWidgetItem()
            item.setText(COL_NAME, display_name)
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
                    item.setToolTip(column, self.tr("Story is hidden for LuniiStore synchronization"))
                    item.setForeground(column, grey_color)

            self.tree_stories.addTopLevelItem(item)
            path = "" if local_story is None or DB_LOCAL_LIBRARY_COL_PATH not in local_story else local_story[DB_LOCAL_LIBRARY_COL_PATH]
            data_list.append({"name": display_name, "id": story.str_uuid, "local_db_path": path, "lunii_story_id": story.short_uuid})

        model = SimpleLazyLoadingModel(data_list)
        self.list_stories.setItemDelegate(FixedSizeDelegate())
        self.list_stories.setModel(model)

    def ts_populate_official(self):
        # creating font
        console_font = QFont()
        console_font.setFamilies([u"Consolas"])

        # getting filter text
        le_filter = self.le_filter.text()
        filtered_languages = self.settings.displayed_languages

        # adding items
        data_list = []
        for id in stories.DB_OFFICIAL:
            name = stories.DB_OFFICIAL[id]["title"]
            age = str(stories.DB_OFFICIAL[id]["age_min"])
            filter_name = f'{age}+ {name}'
            lang = list(stories.DB_OFFICIAL[id]["locales_available"].keys())[0]
            filter_language = len(filtered_languages) > 0 and lang not in filtered_languages

            local_story = None if id not in stories.DB_LOCAL_LIBRARY else stories.DB_LOCAL_LIBRARY[id]
            lunii_story = None if self.audio_device is None else self.audio_device.stories.get_story(id)
            # create and add item to treeWidget
            item = NaturalSortTreeWidgetItem()

            if local_story is not None and DB_LOCAL_LIBRARY_COL_PATH in local_story:
                path = local_story[DB_LOCAL_LIBRARY_COL_PATH]
                if os.path.isfile(path):
                    item.setText(COL_OFFICIAL_PATH, path)
                    item.setText(COL_OFFICIAL_SIZE, f"{round(os.path.getsize(path)/1024/1024, 1)}MB")
            elif not self.settings.show_unavailable_stories:
                continue

            # filtering
            if (filter_language or (
                le_filter and
                not le_filter.lower() in item.text(COL_OFFICIAL_PATH).lower() and
                not le_filter.lower() in filter_name.lower() and
                not le_filter.lower() in id.lower())):
                continue

            if self.settings.filtered_min_age and age < self.settings.filtered_min_age:
                continue
            
            if self.settings.filtered_max_age and age > self.settings.filtered_max_age:
                continue
      
            item.setText(COL_OFFICIAL_NAME, name)
            item.setText(COL_OFFICIAL_UUID, id)
            item.setFont(COL_OFFICIAL_UUID, console_font)
            item.setText(COL_OFFICIAL_AGE, age)
            item.setText(COL_OFFICIAL_LANGUAGE, lang)

            if lunii_story is not None:
                item.setText(COL_OFFICIAL_INSTALLED, lunii_story.short_uuid)

            self.tree_stories_official.addTopLevelItem(item)

            local_db_path = item.text(COL_OFFICIAL_PATH)
            lunii_story_id = item.text(COL_OFFICIAL_INSTALLED)

            display_name = item.text(COL_OFFICIAL_AGE) + "+ " + item.text(COL_OFFICIAL_NAME)
            data_list.append({"name": display_name, "id": id, "local_db_path": local_db_path, "lunii_story_id": lunii_story_id})

        model = SimpleLazyLoadingModel(data_list)
        sorted_model = NaturalSortProxyModel()
        sorted_model.setSourceModel(model)
        sorted_model.sort(0)
        self.list_stories_official.setItemDelegate(FixedSizeDelegate())
        self.list_stories_official.setModel(sorted_model)

    def ts_populate_third_party(self):
        # creating font
        console_font = QFont()
        console_font.setFamilies([u"Consolas"])

        # getting filter text
        le_filter = self.le_filter.text()

        # adding items
        data_list = []
        for id in stories.DB_THIRD_PARTY:
            name = stories.DB_THIRD_PARTY[id]["title"]
            if name is None or name == "":
                continue

            local_story = None if id not in stories.DB_LOCAL_LIBRARY else stories.DB_LOCAL_LIBRARY[id]
            lunii_story = None if self.audio_device is None else self.audio_device.stories.get_story(id)

            # create and add item to treeWidget
            item = NaturalSortTreeWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            age = "" if local_story is None or DB_LOCAL_LIBRARY_COL_AGE not in local_story else local_story[DB_LOCAL_LIBRARY_COL_AGE]
            
            display_name = name if local_story is None or not DB_LOCAL_LIBRARY_COL_NAME in local_story else local_story[DB_LOCAL_LIBRARY_COL_NAME]
            display_name_with_age = display_name if age == "" else f'{age}+ {display_name}'

            if local_story is not None and DB_LOCAL_LIBRARY_COL_PATH in local_story:
                path = local_story[DB_LOCAL_LIBRARY_COL_PATH]
                if os.path.isfile(path):
                    item.setText(COL_THIRD_PARTY_PATH, path)
                    item.setText(COL_THIRD_PARTY_SIZE, f"{round(os.path.getsize(path)/1024/1024, 1)}MB")
            elif not self.settings.show_unavailable_stories:
                continue

            # filtering
            if (le_filter and
                not le_filter.lower() in item.text(COL_THIRD_PARTY_PATH).lower() and
                not le_filter.lower() in display_name_with_age.lower() and
                not le_filter.lower() in id.lower() ):
                continue

            if self.settings.filtered_min_age and age != "" and age < self.settings.filtered_min_age:
                continue
            
            if self.settings.filtered_max_age and age != "" and age > self.settings.filtered_max_age:
                continue
            
            item.setText(COL_THIRD_PARTY_NAME, display_name)
            item.setText(COL_THIRD_PARTY_UUID, id)
            item.setFont(COL_THIRD_PARTY_UUID, console_font)
            item.setText(COL_THIRD_PARTY_AGE, age)

            if lunii_story is not None:
                item.setText(COL_THIRD_PARTY_INSTALLED, lunii_story.short_uuid)

            self.tree_stories_third_party.addTopLevelItem(item)

            local_db_path = item.text(COL_THIRD_PARTY_PATH)
            lunii_story_id = item.text(COL_THIRD_PARTY_INSTALLED)

            data_list.append({"name": display_name_with_age, "id": id, "local_db_path": local_db_path, "lunii_story_id": lunii_story_id})

        model = SimpleLazyLoadingModel(data_list)
        sorted_model = NaturalSortProxyModel()
        sorted_model.setSourceModel(model)
        sorted_model.sort(0)
        self.list_stories_third_party.setItemDelegate(FixedSizeDelegate())
        self.list_stories_third_party.setModel(sorted_model)

    def sb_create(self):
        self.statusBar().showMessage("bla-bla bla")
        self.lbl_hsnu = QLabel("SNU:")
        self.lbl_snu = QLabel()
        self.lbl_version = QLabel()
        self.lbl_hfs = QLabel(self.tr("Free :"))
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
            self.lbl_count.setText(f"{count_items} " + self.tr("stories"))
        else:
            self.lbl_count.setText("")

    def cb_nm(self):
        result = self.nm_dialog.exec()

        if result == QDialog.Accepted:
            self.audio_device.config = self.nm_dialog.config
            self.audio_device.update_config()

            # updating button image
            self.cb_nm_update_btn()

    def cb_nm_update_btn(self):
        icon_nm = QIcon()
        if self.audio_device and self.audio_device.device_version != FLAM_V1 and self.audio_device.config[LUNII_CFGPOS_NM_ENABLED] == 1:
            icon_nm.addFile(u":/icon/res/mode_night.png", QSize(), QIcon.Normal, QIcon.Off)
        else:
            icon_nm.addFile(u":/icon/res/mode_day.png", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_nightmode.setIcon(icon_nm)

    def ts_move(self, offset):
        if self.worker or not self.audio_device:
            return

        # start = time.time()

        # shifting to be right is shifting to the left the reverse list
        if offset >= 1:
            self.audio_device.stories.reverse()

        working_list = [[story, index+1] for index, story in enumerate(self.audio_device.stories)]

        # getting selection
        selected_items = self.get_multiple_selection()
        if len(selected_items) == 0:
            return
        
        items_to_move = [id for (id, _) in selected_items]

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
        selected_items = self.get_multiple_selection()
        if len(selected_items) == 0:
            return
        items_ids = [id for (id, _) in selected_items]


        # preparing validation window
        dlg = QMessageBox(self)
        dlg.setWindowTitle(self.tr("Delete stories"))
        message = self.tr("You are requesting to delete : \n")
        for (_, name) in selected_items:
            message += f"- {name}\n"

        if len(message) > 512:
            message = message[:768] + "..."
            message += self.tr("\n(and too many others)\n")

        message += self.tr("\nDo you want to proceed ?")
        dlg.setText(message)
        dlg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        dlg.setIcon(QMessageBox.Warning)
        button = dlg.exec_()

        if button != QMessageBox.Ok:
            return

        self.audio_player.stop(True)
        # processing selection
        self.worker_launch(ACTION_REMOVE, items_ids)

    def ts_export(self):
        # getting selection
        selected_items = self.get_multiple_selection()
        if len(selected_items) == 0:
            return

        out_dir = QFileDialog.getExistingDirectory(self, f"Output Directory for {len(selected_items)} stories", "",
                                                   QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)

        # if ok pressed
        if out_dir:
            self.worker_launch(ACTION_EXPORT, [id for (id, _) in selected_items], out_dir)
        else:
            self.sb_update(self.tr("🛑 Export cancelled"))

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
            self.sb_update(self.tr("🛑 Export All cancelled"))

    def ts_save_pack(self):
        # getting selection
        selected_items = self.get_multiple_selection()
        if len(selected_items) == 0:
            return

        (file, _) = QFileDialog.getSaveFileName(self, f'Save pack with {len(selected_items)} stories: {", ".join([name for (_, name) in selected_items])}', "", self.tr("Json Files (*.json);;All Files (*)"))
        with open(file, "w", encoding="utf-8") as f:
            data = []
            for (id, name) in selected_items:
                if id in stories.DB_LOCAL_LIBRARY and DB_LOCAL_LIBRARY_COL_PATH in stories.DB_LOCAL_LIBRARY[id] and len(stories.DB_LOCAL_LIBRARY[id][DB_LOCAL_LIBRARY_COL_PATH]) > 0:
                    data.append([name, id, stories.DB_LOCAL_LIBRARY[id][DB_LOCAL_LIBRARY_COL_PATH]])
                else:
                    self.sb_update(self.tr(f"⚠️ Local file not available for {name} - {id}."))

            self.sb_update(self.tr(f"Pack saved to '{file}' with {len(data)} stories."))
            json.dump(data, f, indent=4)

    def ts_load_pack(self):
        (file, _) = QFileDialog.getOpenFileName(self, f"Open a story pack", "", self.tr("Json Files (*.json);;All Files (*)"))
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.sb_update(self.tr(f"Loading pack '{file}' with {len(data)} stories:"))
        files = []
        for item in data:
            story_name = item[0]
            story_uuid = item[1]
            story_path = item[2]
            if os.path.isfile(story_path):
                self.sb_update(self.tr(f"\t- {story_name} - {story_uuid} at '{story_path}'"))
                files.append(story_path)
            else:
                self.sb_update(self.tr(f"⚠️ Local file not available for {story_name} - {story_uuid} at '{story_path}'."))

        self.worker_launch(ACTION_IMPORT, files)


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

            # moving to hidden directory
            story_dir = os.path.join(self.audio_device.mount_point, self.audio_device.STORIES_BASEDIR)
            story_hiddendir = os.path.join(self.audio_device.mount_point, self.audio_device.HIDDEN_STORIES_BASEDIR)

            # moving story directory to hidden directory
            try:
                if one_story.hidden:
                    # creating hidden dir if not exists
                    os.makedirs(story_hiddendir, exist_ok=True)
                    story_dir = os.path.join(story_dir, one_story.str_uuid.lower() if self.audio_device.device_version == FLAM_V1 else one_story.short_uuid)
                    if os.path.isdir(story_dir):
                        shutil.move(story_dir, story_hiddendir)
                    else:
                        one_story.hidden = not one_story.hidden
                        self.logger.log(logging.ERROR, f"Story dir {story_dir} does not exist or already hidden")
                        self.logger.log(logging.INFO, f"💡 Try to use menu 'Tools/Recover or Remove lost stories' to fix it")
                        self.sb_update(self.tr("🛑 Unable to update story ..."))
                        self.cb_show_log()
                        return
                else:
                    # moving back to stories dir
                    os.makedirs(story_dir, exist_ok=True)
                    story_hiddendir = os.path.join(story_hiddendir, one_story.str_uuid.lower() if self.audio_device.device_version == FLAM_V1 else one_story.short_uuid)
                    if os.path.isdir(story_hiddendir):
                        shutil.move(story_hiddendir, story_dir)
                    else:
                        one_story.hidden = not one_story.hidden
                        self.logger.log(logging.ERROR, f"Hidden story dir {story_hiddendir} does not exist or already visible")
                        self.logger.log(logging.INFO, f"💡 Try to use menu 'Tools/Recover or Remove lost stories' to fix it")
                        self.sb_update(self.tr("🛑 Unable to update story ..."))
                        self.cb_show_log()
                        return
            except shutil.Error as e:
                one_story.hidden = not one_story.hidden
                self.logger.log(logging.ERROR, f"Error occurred while moving story directories: {e}")
                self.logger.log(logging.INFO, f"💡 Try to use menu 'Tools/Recover or Remove lost stories' to fix it")
                self.sb_update(self.tr("🛑 Unable to update story ..."))
                self.cb_show_log()
                return

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

        self.sb_update(self.tr("✅ Stories updated..."))

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
            story_nm = os.path.join(self.audio_device.story_dir(one_story), "nm")
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

        self.sb_update(self.tr("✅ Stories updated..."))

    def ts_import(self):
        if not self.audio_device:
            return

        file_filter = "All supported (*.pk *.7z *.zip);;PK files (*.plain.pk *.pk);;Archive files (*.7z *.zip);;All files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, self.tr("Open Stories"), "", file_filter)

        if not files:
            return

        self.sb_update(self.tr("Importing stories..."))
        self.worker_launch(ACTION_IMPORT, files)

    def ts_import_in_library(self):
        file_filter = "All supported (*.pk *.7z *.zip);;PK files (*.plain.pk *.pk);;Archive files (*.7z *.zip);;All files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, self.tr("Open Stories"), "", file_filter)

        if files:
            self.sb_update(self.tr("Importing stories in local library..."))
            self.worker_launch(ACTION_IMPORT_IN_LIBRAIRY, files)

        self.ts_update()

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
        if self.audio_device.device_version == LUNII_V3 and not self.audio_device.story_key:
            self.sb_update(self.tr("🛑 Unable to import story, missing story key for Lunii v3"))
            return

        # getting path for dropped files
        file_paths = [url.toLocalFile() for url in event.mimeData().urls()]

        self.sb_update(self.tr("Importing stories..."))
        self.worker_launch(ACTION_IMPORT, file_paths)

    def ts_clicked(self, item, column):
        if column == COL_NM:
            self.ts_nm()

    def lock_ui(self):
        self.tree_stories.setEnabled(False)
        self.list_stories.setEnabled(False)
        self.tree_stories_official.setEnabled(False)
        self.list_stories_official.setEnabled(False)
        self.tabWidget.setEnabled(False)
        self.btn_db.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.combo_device.setEnabled(False)
        self.add_story_button.setEnabled(False)
        self.remove_story_button.setEnabled(False)
        self.combo_language_filter.setEnabled(False)
        self.combo_age_min_filter.setEnabled(False)
        self.combo_age_max_filter.setEnabled(False)

    def unlock_ui(self):
        self.tree_stories.setEnabled(True)
        self.list_stories.setEnabled(True)
        self.tree_stories_official.setEnabled(True)
        self.list_stories_official.setEnabled(True)
        self.tabWidget.setEnabled(True)
        self.btn_db.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.combo_device.setEnabled(True)
        self.add_story_button.setEnabled(True)
        self.remove_story_button.setEnabled(True)
        self.combo_language_filter.setEnabled(self.tabWidget.currentIndex() == 1)
        self.combo_age_min_filter.setEnabled(self.tabWidget.currentIndex() != 0)
        self.combo_age_max_filter.setEnabled(self.tabWidget.currentIndex() != 0)

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
        self.worker = ierWorker(self.audio_device, action, item_list, out_dir, not self.settings.sizes_hidden and action == ACTION_IMPORT)
        self.thread = QtCore.QThread()
        self.worker.moveToThread(self.thread)

        # UI limitations
        self.lock_ui()

        # connecting slots
        self.thread.started.connect(self.worker.process)
        self.worker.signal_finished.connect(self.slot_finished)
        # self.worker.signal_finished.connect(self.worker.deleteLater)
        # self.thread.finished.connect(self.thread.deleteLater)

        # UI update slots
        if self.audio_device:
            self.audio_device.signal_story_progress.connect(self.slot_story_progress)
            self.audio_device.signal_file_progress.connect(self.slot_file_progress)
            self.audio_device.signal_logger.connect(self.logger.log)
        self.worker.signal_total_progress.connect(self.slot_total_progress, QtCore.Qt.QueuedConnection)
        self.worker.signal_finished.connect(self.thread.quit, QtCore.Qt.QueuedConnection)
        self.worker.signal_refresh.connect(self.ts_update, QtCore.Qt.QueuedConnection)
        self.worker.signal_message.connect(self.sb_update, QtCore.Qt.QueuedConnection)
        self.worker.signal_showlog.connect(self.cb_show_log, QtCore.Qt.QueuedConnection)

        # running
        self.thread.start()

    def worker_abort(self):
        if not self.worker:
            return

        # pushing message
        self.sb_update(self.tr("Abort requested, please wait..."))

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

    def slot_story_progress(self, uuid, story_current, story_max_val):
        # updating UI
        self.lbl_story.setVisible(True)
        self.lbl_story.setText(uuid)

        self.pbar_story.setVisible(True)
        self.pbar_story.setRange(0, story_max_val)
        self.pbar_story.setValue(story_current+1)

        self.btn_abort.setVisible(True)

    def slot_file_progress(self, speed, file_current, file_max_val):
        # updating UI
        self.lbl_story.setVisible(True)
        self.lbl_story.setText(speed)

        if file_max_val:
            self.pbar_file.setVisible(True)
            self.pbar_file.setRange(0, file_max_val)
            self.pbar_file.setValue(file_current if file_current < file_max_val else 0)
        else:
            self.pbar_file.setVisible(False)


    def slot_finished(self):
        # print("SLOT FINISHED")
        # updating UI
        self.unlock_ui()

        # hiding progress
        self.lbl_total.setVisible(False)
        self.pbar_total.setVisible(False)
        self.lbl_story.setVisible(False)
        self.pbar_story.setVisible(False)
        self.pbar_file.setVisible(False)
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


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class NaturalSortTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        col = self.treeWidget().sortColumn()
        self_data = self.text(col)
        other_data = other.text(col)
        return natural_sort_key(self_data) < natural_sort_key(other_data)

class NaturalSortProxyModel(QSortFilterProxyModel):
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)
        return natural_sort_key(left_data) < natural_sort_key(right_data)

class ColumnEditableDelegate(QStyledItemDelegate):
    def __init__(self, editable_columns, parent=None):
        super().__init__(parent)
        self.editable_columns = set(editable_columns)

    def createEditor(self, parent, option, index):
        if index.column() in self.editable_columns:
            return super().createEditor(parent, option, index)
        return None

class VLine(QFrame):
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)
import os.path
# import time
from pathlib import WindowsPath
from uuid import UUID

import psutil
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QFileDialog, QMessageBox, QLabel, QFrame
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QPixmap, Qt

from pkg.api.device import find_devices, LuniiDevice, is_device
from pkg.api.stories import story_load_db, story_name, story_desc, DESC_NOT_FOUND, story_load_pict
from pkg.api.constants import *
from pkg.ierWorker import ierWorker, ACTION_REMOVE, ACTION_IMPORT, ACTION_EXPORT

from pkg.ui.main_ui import Ui_MainWindow

"""
TODO : 
 * drag n drop to reorder list
DONE
 * add cache mgmt in home dir (or local)
 * download story icon
 * display picture
 * add icon to app
 * add icon to refresh button
 * add icon to context menu
 * supporting entry for lunii path
 * create a dedicated thread for import / export / delete
 * Add free space
 * select move up/down reset screen display
"""

COL_NAME = 0
COL_UUID = 1
APP_VERSION = "v2.0.7"


class VLine(QFrame):
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        # class instance vars init
        self.lunii_device: LuniiDevice = None
        self.worker: ierWorker = None
        self.thread: QtCore.QThread = None
        self.app = app

        # UI init
        self.app.processEvents()
        self.init_ui()
        self.app.processEvents()

        # loading DB
        story_load_db(False)


    def init_ui(self):
        self.setupUi(self)
        self.modify_widgets()
        self.setup_connections()
        self.cb_dev_refresh()

    # update ui elements state (enable, disable, context enu)
    def modify_widgets(self):
        self.setWindowTitle(f"Lunii Qt-Manager {APP_VERSION}")

        self.btn_about.setVisible(False)
        # self.pgb_total.setVisible(False)
        self.tree_stories.setColumnWidth(0, 300)
        self.lbl_picture.setVisible(False)
        self.te_story_details.setVisible(False)

        # clean progress bars
        self.lbl_total.setVisible(False)
        self.pbar_total.setVisible(False)
        self.lbl_story.setVisible(False)
        self.pbar_story.setVisible(False)

        # Connect the context menu
        self.tree_stories.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_stories.customContextMenuRequested.connect(self.ts_context_menu)
        self.__ctxmenu_create()

        # Update statusbar
        self.__sb_create()

    def __ctxmenu_create(self):
        # We build the menu.
        self.menu = QtWidgets.QMenu()
        self.act_mv_up = self.menu.addAction("Move Up")
        self.act_mv_down = self.menu.addAction("Move Down")
        self.menu.addSeparator()
        self.act_import = self.menu.addAction("Import")
        self.act_export = self.menu.addAction("Export")
        self.act_remove = self.menu.addAction("Remove")

        # config Tooltips
        self.act_mv_up.setToolTip("Move item upper (ATL + UP)")
        self.act_mv_down.setToolTip("Move item upper (ATL + DOWN)")
        self.act_import.setToolTip("Export story to Archive")
        self.act_export.setToolTip("Import story from Archive")
        self.act_remove.setToolTip("Remove story")

        # Loading icons
        icon = QtGui.QIcon()

        icon.addPixmap(QtGui.QPixmap(":/icon/res/up.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.act_mv_up.setIcon(icon)
        icon.addPixmap(QtGui.QPixmap(":/icon/res/down.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.act_mv_down.setIcon(icon)
        icon.addPixmap(QtGui.QPixmap(":/icon/res/import.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.act_import.setIcon(icon)
        icon.addPixmap(QtGui.QPixmap(":/icon/res/export.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.act_export.setIcon(icon)
        icon.addPixmap(QtGui.QPixmap(":/icon/res/remove.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.act_remove.setIcon(icon)

    def __ctxmenu_update(self, index):
        self.act_mv_up.setEnabled(False)
        self.act_mv_down.setEnabled(False)
        self.act_import.setEnabled(False)
        self.act_export.setEnabled(False)
        self.act_remove.setEnabled(False)

        # during download or no device selected, no action possible
        if not self.lunii_device or self.worker:
            return

        # always possible to import in an empty device
        self.act_import.setEnabled(True)

        # pointing to an item
        if index.isValid():
            self.act_mv_up.setEnabled(True)
            self.act_mv_down.setEnabled(True)
            self.act_remove.setEnabled(True)

            # v3 without keys cannot export
            if (self.lunii_device.lunii_version < LUNII_V3 or
                    (self.lunii_device.lunii_version == LUNII_V3 and self.lunii_device.device_key)):
                self.act_export.setEnabled(True)

    def __sb_create(self):
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

    # connecting slots and signals
    def setup_connections(self):
        self.combo_device.currentIndexChanged.connect(self.cb_dev_select)
        self.le_filter.textChanged.connect(self.ts_update)
        self.btn_refresh.clicked.connect(self.cb_dev_refresh)
        self.btn_db.clicked.connect(self.cb_db_refresh)
        self.tree_stories.itemSelectionChanged.connect(self.cb_tree_select)
        self.tree_stories.installEventFilter(self)

        # signals connections
        # LuniiDevice.signal_zip_progress.connect(self.slot_zip_progress)

        # story list shortcuts
        QShortcut(QKeySequence("Alt+Up"), self.tree_stories, self.ts_move_up)
        QShortcut(QKeySequence("Alt+Down"), self.tree_stories, self.ts_move_down)
        QShortcut(QKeySequence("Delete"), self.tree_stories, self.ts_remove)
        QShortcut(QKeySequence("Ctrl+S"), self.tree_stories, self.ts_export)
        QShortcut(QKeySequence("Ctrl+I"), self.tree_stories, self.ts_import)
        QShortcut(QKeySequence("F5"), self, self.cb_dev_refresh)

    def eventFilter(self, obj, event):
        if obj.objectName() == "tree_stories":
            if event.type() == QtCore.QEvent.DragEnter:
                self.ts_dragenter_action(event)
                return True
            elif event.type() == QtCore.QEvent.Drop:
                self.ts_drop_action(event)
                return True
        return False

    # TREE WIDGET MANAGEMENT
    def ts_context_menu(self, point):
        # about the selected node.
        index = self.tree_stories.indexAt(point)

        self.__ctxmenu_update(index)

        # Checking action
        picked_action = self.menu.exec_(self.tree_stories.mapToGlobal(point))
        if picked_action == self.act_mv_up:
            self.ts_move_up()
        elif picked_action == self.act_mv_down:
            self.ts_move_down()
        elif picked_action == self.act_import:
            self.ts_import()
        elif picked_action == self.act_export:
            self.ts_export()
        elif picked_action == self.act_remove:
            self.ts_remove()

    # WIDGETS UPDATES
    def cb_dev_refresh(self):
        dev_list = find_devices()
        self.combo_device.clear()
        self.lunii_device = None

        dev: WindowsPath
        self.combo_device.setPlaceholderText("Select your Lunii")
        self.sb_update("")

        for dev in dev_list:
            dev_name = str(dev)
            # print(dev_name)
            self.combo_device.addItem(dev_name)

        if os.path.isdir("C:/Work/dev/lunii-packs/test/"):
            self.combo_device.addItem("C:/Work/dev/lunii-packs/test/_v1/")
            self.combo_device.addItem("C:/Work/dev/lunii-packs/test/_v2/")
            self.combo_device.addItem("C:/Work/dev/lunii-packs/test/_v3/")

        if self.combo_device.count():
            self.combo_device.lineEdit().setText("Select your Lunii")

            # automatic select if only one device
            if self.combo_device.count() == 1:
                self.combo_device.setCurrentIndex(0)
        else:
            self.statusbar.showMessage("No Lunii detected 😥, try to copy paste a path")
            self.combo_device.lineEdit().setText("Enter a path here")

    def cb_dev_select(self):
        # getting current device
        dev_name = self.combo_device.currentText()

        if dev_name:

            if not is_device(dev_name):
                self.statusbar.showMessage(f"ERROR : {dev_name} is not a recognized Lunii.")

                # removing the new entry
                cur_index = self.combo_device.currentIndex()
                self.combo_device.removeItem(cur_index)

                # picking another existing entry
                if self.combo_device.count() > 0:
                    self.combo_device.setCurrentIndex(0)
                else:
                    self.combo_device.lineEdit().setText("Enter a path here")

                return

            self.lunii_device = LuniiDevice(dev_name, V3_KEYS)
            self.statusbar.showMessage(f"")

            self.ts_update()
            self.sb_update("")

    def cb_tree_select(self):
        # getting selection
        selection = self.tree_stories.selectedItems()
        only_one = len(selection) == 1
        # self.lbl_picture.setVisible(only_one)
        self.te_story_details.setVisible(only_one)
        self.lbl_picture.setVisible(only_one)

        if only_one:
            item = selection[0]
            uuid = item.text(COL_UUID)

            one_story_desc = story_desc(uuid)
            one_story_image = story_load_pict(uuid)

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

    def ts_update(self):
        # clear previous story list
        self.tree_stories.clear()
        self.ts_populate()
        # update status in status bar
        # self.sb_update_summary()

    def ts_populate(self):
        # empty device
        if not self.lunii_device or not self.lunii_device.stories or len(self.lunii_device.stories) == 0:
            return

        # creating font
        console_font = QFont()
        console_font.setFamilies([u"Consolas"])

        # getting filter text
        le_filter = self.le_filter.text()

        # adding items
        for story in self.lunii_device.stories:
            # filtering 
            if le_filter is not None and le_filter.lower() not in story_name(story).lower():
                continue

            # create and add item to treeWidget
            item = QTreeWidgetItem()
            item.setText(COL_NAME, story_name(story))
            item.setText(COL_UUID, str(story).upper())
            item.setFont(COL_UUID, console_font)
            self.tree_stories.addTopLevelItem(item)

    def sb_update(self, message):
        self.lbl_snu.setText("")
        self.lbl_version.setText("")
        self.lbl_fs.setText("")
        self.lbl_count.setText("")
        self.statusbar.showMessage(message)

        if not self.lunii_device:
            return

        # SNU
        self.lbl_snu.setText(self.lunii_device.snu.hex().upper().lstrip("0"))
        # self.lbl_snu.setText("23023030012345")

        # Version
        version = ""
        if self.lunii_device.lunii_version == LUNII_V1:
            HW_version = "v1"
            SW_version = f"{self.lunii_device.fw_vers_major}.{self.lunii_device.fw_vers_minor}"
        elif self.lunii_device.lunii_version == LUNII_V2:
            HW_version = "v2"
            SW_version = f"{self.lunii_device.fw_vers_major}.{self.lunii_device.fw_vers_minor}"
        elif self.lunii_device.lunii_version == LUNII_V3:
            HW_version = "v3"
            SW_version = f"{self.lunii_device.fw_vers_major}.{self.lunii_device.fw_vers_minor}.{self.lunii_device.fw_vers_subminor}"
        self.lbl_version.setText(f"Lunii {HW_version}, FW: {SW_version}")

        # Free Space
        free_space = psutil.disk_usage(str(self.lunii_device.mount_point)).free
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

    def ts_move_up(self):
        # print("ts_move_up")
        self.ts_move(-1)

    def ts_move_down(self):
        # print("ts_move_down")
        self.ts_move(1)

    def ts_move(self, offset):
        # # no moves under filters
        # if self.le_filter.text():
        #     self.statusbar.showMessage("Remove filters before moving...")
        #     return

        # start = time.time()

        # getting selection
        # selected = self.tree_stories.selectionModel().selection()
        if self.worker or not self.lunii_device:
            return

        selected_items = self.tree_stories.selectedItems()
        if len(selected_items) == 0:
            return

        old_idx = set()
        # getting all indexes to move (sorted)
        for item in selected_items:
            old_idx.add(self.lunii_device.stories.index(UUID(item.text(COL_UUID))))

        old_idx = sorted(old_idx)

        # updating new indexes
        new_idx = list()
        for pos, idx in enumerate(old_idx):
            # top reached ?
            if offset < 0 and idx <= pos:
                new_idx.append(idx)
                continue

            # bottom reached ?
            if offset > 0 and idx >= len(self.lunii_device.stories) - 1 - (len(old_idx) - 1 - pos):
                new_idx.append(idx)
                continue

            new_idx.append(idx + offset)

        # moving items
        for i in range(len(new_idx)):
            # depending on offset (up / down), list must be updated in specific order
            if offset > 0:
                i = len(new_idx) - 1 - i

            # print(f"{old_idx[i]} -> {new_idx[i]}")
            if old_idx[i] != new_idx[i]:
                self.lunii_device.stories.insert(new_idx[i], self.lunii_device.stories.pop(old_idx[i]))

        # update Lunii device (.pi)
        self.lunii_device.update_pack_index()

        # refresh stories
        self.ts_update()

        # update selection
        sel_model = self.tree_stories.selectionModel()
        # sel_model.select(selected, QItemSelectionModel.Select)
        for idx in new_idx:
            item: QTreeWidgetItem = self.tree_stories.topLevelItem(idx)
            sel_model.select(self.tree_stories.indexFromItem(item, COL_NAME), QItemSelectionModel.Select)
            sel_model.select(self.tree_stories.indexFromItem(item, COL_UUID), QItemSelectionModel.Select)

        # update scroll bar pos
        selected_items = self.tree_stories.selectedItems()
        self.tree_stories.scrollToItem(selected_items[0])

        # end = time.time()
        # print(f"took {end-start:02.2}s")

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

        out_dir = QFileDialog.getExistingDirectory(self, "Ouput Directory for Stories", "",
                                                   QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)

        # if ok pressed
        if out_dir:
            to_export = [item.text(COL_UUID) for item in selection]
            self.worker_launch(ACTION_EXPORT, to_export, out_dir)

    def ts_import(self):
        if not self.lunii_device:
            return

        file_filter = "PK files (*.plain.pk *.pk);;Archive files (*.7z *.zip);;All supported (*.pk *.7z *.zip);;All files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Open Stories", "", file_filter)

        if not files:
            return

        self.worker_launch(ACTION_IMPORT, files)

    def ts_dragenter_action(self, event):
        # a Lunii must be selected
        if not self.lunii_device:
            event.ignore()
            return

        # must be files
        if event.mimeData().hasUrls():
            # getting path for dropped files
            file_paths = [url.toLocalFile() for url in event.mimeData().urls()]

            # checking if dropped files are ending with expected extensions
            if all(any(file.endswith(ext) for ext in SUPPORTED_EXT) for file in file_paths):
                event.acceptProposedAction()
            else:
                event.ignore()

    def ts_drop_action(self, event):
        # getting path for dropped files
        file_paths = [url.toLocalFile() for url in event.mimeData().urls()]

        self.worker_launch(ACTION_IMPORT, file_paths)

    def worker_launch(self, action, item_list, out_dir=None):
        if self.worker:
            return

        # setting up the thread
        self.worker = ierWorker(self.lunii_device, action, item_list, out_dir)
        self.thread = QtCore.QThread()
        self.worker.moveToThread(self.thread)

        # UI limitations
        self.btn_db.setEnabled(False)
        self.tree_stories.setEnabled(False)

        # connecting slots
        self.thread.started.connect(self.worker.process)
        self.worker.signal_finished.connect(self.thread.quit)
        self.worker.signal_total_progress.connect(self.slot_total_progress)
        self.lunii_device.signal_story_progress.connect(self.slot_story_progress)
        self.worker.signal_finished.connect(self.slot_finished)
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

        self.worker = None
        self.thread = None

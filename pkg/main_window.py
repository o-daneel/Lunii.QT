import os.path
import time
from pathlib import WindowsPath

import psutil
from PySide6 import QtCore, QtGui
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QFileDialog, QMessageBox, QLabel, QFrame, QHeaderView
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QPixmap, Qt

from pkg.api.device import find_devices, LuniiDevice, is_device
from pkg.api.stories import story_load_db, DESC_NOT_FOUND, StoryList
from pkg.api.constants import *
from pkg.ierWorker import ierWorker, ACTION_REMOVE, ACTION_IMPORT, ACTION_EXPORT, ACTION_SIZE

from pkg.ui.main_ui import Ui_MainWindow

COL_NAME = 0
COL_DB = 1
COL_UUID = 2
COL_SIZE = 3

COL_DB_SIZE = 20
COL_UUID_SIZE = 250
COL_SIZE_SIZE = 90

APP_VERSION = "v2.1.1"


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
        # app config
        self.sizes_hidden = True
        self.details_hidden = False
        self.details_last_uuid = None

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

        # self.menuTools.setEnabled(False)
        # shortcuts lost if not visible
        # self.menuBar.setVisible(False)
        # QShortcut(QKeySequence("Ctrl+Up"), self.tree_stories, self.ts_move_top)
        # QShortcut(QKeySequence("Alt+Up"), self.tree_stories, self.ts_move_up)
        # QShortcut(QKeySequence("Alt+Down"), self.tree_stories, self.ts_move_down)
        # QShortcut(QKeySequence("Ctrl+Down"), self.tree_stories, self.ts_move_bottom)
        # QShortcut(QKeySequence("Delete"), self.tree_stories, self.ts_remove)
        # QShortcut(QKeySequence("Ctrl+S"), self.tree_stories, self.ts_export)
        # QShortcut(QKeySequence("Ctrl+Shift+S"), self.tree_stories, self.ts_export_all)
        # QShortcut(QKeySequence("Ctrl+I"), self.tree_stories, self.ts_import)

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

        # Connect the context menu
        self.tree_stories.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_stories.customContextMenuRequested.connect(self.cb_show_context_menu)

        self.menuFile.triggered.connect(self.cb_menu_file)
        self.menuStory.triggered.connect(self.cb_menu_story)
        self.menuStory.aboutToShow.connect(self.cb_menu_story_update)
        self.menuTools.triggered.connect(self.cb_menu_tools)

        # Update statusbar
        self.sb_create()

        # Update Menu tools based on config
        t_actions = self.menuTools.actions()
        act_details = next(act for act in t_actions if act.objectName() == "actionShow_story_details")
        act_size = next(act for act in t_actions if act.objectName() == "actionShow_size")
        act_details.setChecked(not self.details_hidden)
        act_size.setChecked(not self.sizes_hidden)


    # connecting slots and signals
    def setup_connections(self):
        self.combo_device.currentIndexChanged.connect(self.cb_dev_select)
        self.le_filter.textChanged.connect(self.ts_update)
        self.btn_refresh.clicked.connect(self.cb_dev_refresh)
        self.btn_db.clicked.connect(self.cb_db_refresh)
        self.tree_stories.itemSelectionChanged.connect(self.cb_tree_select)
        self.tree_stories.installEventFilter(self)

        # story list shortcuts
        QShortcut(QKeySequence("F5"), self, self.cb_dev_refresh)

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

    def cb_show_context_menu(self, point):
        # change active menu based on selection
        self.cb_menu_story_update()

        self.menuStory.exec_(self.tree_stories.mapToGlobal(point))

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

            # in case of a worker, abort it
            if self.worker:
                self.worker.early_exit = True
                while self.worker:
                    self.app.processEvents()
                    time.sleep(0.05)

            self.lunii_device = LuniiDevice(dev_name, V3_KEYS)
            self.statusbar.showMessage(f"")

            self.ts_update()
            self.sb_update("")

            # computing sizes if necessary
            if not self.sizes_hidden and any(story for story in self.lunii_device.stories if story.size == -1):
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
            one_story = self.lunii_device.stories.get_story(uuid)
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

    def cb_menu_file(self, action: QtGui.QAction):
        act_name = action.objectName()
        if act_name == "actionOpen_Lunii":

            file_filter = "Lunii Metadata (.md);;All files (*)"
            file, _ = QFileDialog.getOpenFileName(self, "Open Lunii device", "", file_filter)

            if not file:
                return

            # check if path is a recognized device
            dev_name = os.path.dirname(file)
            if not is_device(dev_name):
                self.sb_update("Not a Lunii or unsupported one 😥")

            # add device to list
            device_list = [self.combo_device.itemText(i) for i in range(self.combo_device.count())]
            if dev_name not in device_list:
                self.combo_device.addItem(dev_name)
                index = self.combo_device.findText(dev_name)
                self.combo_device.setCurrentIndex(index)

    def cb_menu_story_update(self):
        # all disabled
        for action in self.menuStory.actions():
            action.setEnabled(False)

        # during download or no device selected, no action possible
        if not self.lunii_device or self.worker:
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
            if (self.lunii_device.lunii_version < LUNII_V3 or
                    (self.lunii_device.lunii_version == LUNII_V3 and self.lunii_device.device_key)):
                self.act_export.setEnabled(True)

            # TODO : fix and remove - Thirdparty story export not supported
            selected = self.tree_stories.selectedItems()
            if len(selected) == 1:
                one_story = self.lunii_device.stories.get_story(selected[0].text(COL_UUID))
                if not one_story.is_official():
                    self.act_export.setEnabled(False)


        # are there story loaded ?
        if self.lunii_device.stories:
            if (self.lunii_device.lunii_version < LUNII_V3 or
                    (self.lunii_device.lunii_version == LUNII_V3 and self.lunii_device.device_key)):
                self.act_exportall.setEnabled(True)

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

    def ts_move_top(self):
        self.ts_move(-10)
    def ts_move_up(self):
        self.ts_move(-1)
    def ts_move_down(self):
        self.ts_move(1)
    def ts_move_bottom(self):
        self.ts_move(10)
    def ts_move(self, offset):
        if self.worker or not self.lunii_device:
            return

        # start = time.time()

        # shifting to be right is shifting to the left the reverse list
        if offset >= 1:
            self.lunii_device.stories.reverse()

        working_list = [[story, index+1] for index, story in enumerate(self.lunii_device.stories)]

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
        self.lunii_device.stories = StoryList()
        for story, index in working_list:
            self.lunii_device.stories.append(story)

        # we shifted the reverse list, we need to reverse it one last time
        if offset >= 1:
            self.lunii_device.stories.reverse()

        # # update Lunii device (.pi)
        self.lunii_device.update_pack_index()

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

    def worker_launch(self, action, item_list=None, out_dir=None):
        if self.worker:
            return

        if not self.lunii_device:
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

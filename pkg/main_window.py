from pathlib import WindowsPath
from uuid import UUID

from PySide6.QtCore import QItemSelectionModel, QItemSelection
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QFileDialog
from PySide6.QtGui import QFont, QShortcut, QKeySequence

from pkg.api.device import feed_stories, find_devices
from pkg.api.stories import story_name

from pkg.ui.ui_main import Ui_MainWindow

"""
TODO : 
 * create menu handler to export
 * support Drop to load
 * SUPR to remove
 * ALT + UP to move up
 * ALT + DOWN to move down
 * drag n drop to reorder list
 * F5 to refresh devices, no selection
"""

COL_NAME = 0
COL_UUID = 1


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        # class instance vars init
        self.stories = []

        # UI init
        self.init_ui()

    def init_ui(self):
        self.setupUi(self)
        self.modify_widgets()
        self.setup_connections()
        self.cb_dev_refresh()

    # update ui elements state (enable, disable, context enu)
    def modify_widgets(self):
        # self.btn_abort.setVisible(False)
        # self.pgb_total.setVisible(False)
        self.tree_stories.setColumnWidth(0, 300)
        self.lbl_picture.setVisible(False)
        self.te_story_details.setVisible(False)

        # Connect the context menu
        # self.tw_assets.setContextMenuPolicy(QtCore.Qt.Cus)
        # self.tw_assets.customContextMenuRequested.connect(self.tw_context_menu)

    # connecting slots and signals
    def setup_connections(self):
        self.combo_device.currentIndexChanged.connect(self.cb_dev_select)
        self.le_filter.textChanged.connect(self.ts_update)

        # story list shortcuts
        QShortcut(QKeySequence("Alt+Up"), self.tree_stories, self.ts_move_up)
        QShortcut(QKeySequence("Alt+Down"), self.tree_stories, self.ts_move_down)
        QShortcut(QKeySequence("Delete"), self.tree_stories, self.ts_remove)
        QShortcut(QKeySequence("Ctrl+S"), self.tree_stories, self.ts_export)
        QShortcut(QKeySequence("Ctrl+I"), self.tree_stories, self.ts_import)

    # WIDGETS UPDATES
    def cb_dev_refresh(self):
        dev_list = find_devices()
        self.combo_device.clear()

        dev: WindowsPath
        for dev in dev_list:
            dev_name = str(dev)
            print(dev_name)
            self.combo_device.addItem(dev_name)

    def cb_dev_select(self):
        # getting current device
        dev_name = self.combo_device.currentText()

        if dev_name:
            # feeding stories and display
            self.stories = feed_stories(dev_name)
            self.ts_update()

    def ts_update(self):
        # clear previous story list
        self.tree_stories.clear()
        self.ts_populate()
        # update status in status bar
        self.sb_update_summary()

    def ts_populate(self):
        # empty device
        if self.stories is None or len(self.stories) == 0:
            return

        # creating font
        console_font = QFont()
        console_font.setFamilies([u"Consolas"])

        # getting filter text
        le_filter = self.le_filter.text()

        # adding items
        for story in self.stories:
            # filtering 
            if le_filter is not None and le_filter.lower() not in story_name(story).lower():
                continue

            # create and add item to treeWidget
            item = QTreeWidgetItem()
            item.setText(COL_NAME, story_name(story))
            item.setText(COL_UUID, str(story).upper())
            item.setFont(COL_UUID, console_font)
            self.tree_stories.addTopLevelItem(item)

    def sb_update_summary(self):
        # displayed items
        count_items = self.tree_stories.topLevelItemCount()

        sb_message = f" {count_items}/{len(self.stories)}"
        self.statusbar.showMessage(sb_message)

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

        # getting selection
        selected = self.tree_stories.selectionModel().selection()
        selected_items = self.tree_stories.selectedItems()
        if len(selected_items) == 0:
            return

        old_idx = set()
        # getting all indexes to move (sorted)
        for item in selected_items:
            old_idx.add(self.stories.index(UUID(item.text(COL_UUID))))

        old_idx = sorted(old_idx)

        # updating new indexes
        new_idx = list()
        for pos, idx in enumerate(old_idx):
            # top reached ?
            if offset < 0 and idx <= pos:
                new_idx.append(idx)
                continue

            # bottom reached ?
            if offset > 0 and idx >= len(self.stories) - 1 - (len(old_idx) - 1 - pos):
                new_idx.append(idx)
                continue

            new_idx.append(idx + offset)

        # moving items
        for i in range(len(new_idx)):
            print(f"{old_idx[i]} -> {new_idx[i]}")
            if old_idx[i] != new_idx[i]:
                self.stories.insert(new_idx[i], self.stories.pop(old_idx[i]))

        # update Lunii device (.pi)
        # TODO: update Lunii device (.pi)

        # refresh stories
        self.ts_update()

        # update selection
        sel_model = self.tree_stories.selectionModel()
        # sel_model.select(selected, QItemSelectionModel.Select)
        for idx in new_idx:
            item: QTreeWidgetItem = self.tree_stories.topLevelItem(idx)
            sel_model.select(self.tree_stories.indexFromItem(item, COL_NAME), QItemSelectionModel.Select)
            sel_model.select(self.tree_stories.indexFromItem(item, COL_UUID), QItemSelectionModel.Select)

    def ts_remove(self):
        # getting selection
        selection = self.tree_stories.selectedItems()
        if len(selection) == 0:
            return

        # processing selection
        for item in selection:
            uuid = item.text(COL_UUID)
            self.stories.remove(UUID(uuid))

        # update Lunii device (.pi)
        # TODO: update Lunii device (.pi)

        # refresh stories
        self.ts_update()

    def ts_export(self):
        print("ts_export")

        # getting selection
        selection = self.tree_stories.selectedItems()
        if len(selection) == 0:
            return

        # depending on how many files selected
        if len(selection) == 1:
            # save one file only

            # preparing filename
            save_fn = f"{selection[0].text(COL_NAME)}.({selection[0].text(COL_UUID)[-8:]}).zip"

            # creating dialog box
            filename = QFileDialog.getSaveFileName(self, "Save Story", save_fn, "Zip files (*.zip)")
            print(filename)

            # TODO: Save current file
        else:
            # picking an output directory
            out_dir = QFileDialog.getExistingDirectory(self, "Ouput Directory for Stories", "",
                                                       QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
            print(out_dir)

            # TODO: Save all files

        # update Lunii device (.pi)
        #

    def ts_import(self):
        print("ts_import")

        filenames = QFileDialog.getOpenFileName(self, "Open Stories", "", "Zip files (*.zip)")
        print(filenames)

        # update Lunii device (.pi)
        #

        # refresh stories
        self.ts_update()

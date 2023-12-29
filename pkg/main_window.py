from pathlib import WindowsPath
from uuid import UUID

import requests
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QFileDialog, QMessageBox
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QPixmap, Qt

from pkg.api.device import find_devices, LuniiDevice
from pkg.api.stories import story_name, story_desc, story_pict, DESC_NOT_FOUND
from pkg.api.constants import *

from pkg.ui.main_ui import Ui_MainWindow

"""
TODO : 
 * Add free space
 * add icon to context menu
 * add icon to app
 * add icon to refresh button
 * drag n drop to reorder list
 * select move up/down reset screen display
 * create a dedicated thread for import / export / delete
 * add cache mgmt in home dir (or local)
DONE
 * download story icon
 * display picture
"""

COL_NAME = 0
COL_UUID = 1


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        # class instance vars init
        self.lunii_device: LuniiDevice = None
        self.worker = None

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

        # clean progress bars
        self.lbl_total.setVisible(False)
        self.pbar_total.setVisible(False)
        self.lbl_story.setVisible(False)
        self.pbar_story.setVisible(False)

        # Connect the context menu
        self.tree_stories.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_stories.customContextMenuRequested.connect(self.ts_context_menu)

    # connecting slots and signals
    def setup_connections(self):
        self.combo_device.currentIndexChanged.connect(self.cb_dev_select)
        self.le_filter.textChanged.connect(self.ts_update)
        self.btn_refresh.clicked.connect(self.cb_dev_refresh)
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

        # We build the menu.
        menu = QtWidgets.QMenu()
        act_mv_up = menu.addAction("Move Up")
        act_mv_down = menu.addAction("Move Down")
        menu.addSeparator()
        act_import = menu.addAction("Import")
        act_export = menu.addAction("Export")
        act_remove = menu.addAction("Remove")
        menu.addSeparator()
        act_token = menu.addAction("Generate Token")

        act_mv_up.setToolTip("Move item upper (ATL + UP)")
        act_mv_down.setToolTip("Move item upper (ATL + DOWN)")
        act_import.setToolTip("Export story to Archive")
        act_export.setToolTip("Import story from Archive")
        act_remove.setToolTip("Remove story")
        act_token.setToolTip("Rebuild authorization token")

        # not pointing to an item
        if not index.isValid():
            act_mv_up.setEnabled(False)
            act_mv_down.setEnabled(False)
            act_export.setEnabled(False)
            act_remove.setEnabled(False)
            act_token.setEnabled(False)

        if not self.lunii_device or self.worker:
            # during download or no device selected, no action possible
            act_mv_up.setEnabled(False)
            act_mv_down.setEnabled(False)
            act_import.setEnabled(False)
            act_export.setEnabled(False)
            act_remove.setEnabled(False)
            act_token.setEnabled(False)

        if self.lunii_device.lunii_version == LUNII_V3:
            act_token.setEnabled(False)

        # Checking action
        picked_action = menu.exec_(self.tree_stories.mapToGlobal(point))
        if picked_action == act_mv_up:
            self.ts_move_up()
        elif picked_action == act_mv_down:
            self.ts_move_down()
        elif picked_action == act_import:
            self.ts_import()
        elif picked_action == act_export:
            self.ts_export()
        elif picked_action == act_remove:
            self.ts_remove()
        elif picked_action == act_token:
            # TODO : force auth token generation
            pass

    # WIDGETS UPDATES
    def cb_dev_refresh(self):
        dev_list = find_devices()
        self.combo_device.clear()

        dev: WindowsPath
        self.combo_device.setPlaceholderText("Select your Lunii")

        for dev in dev_list:
            dev_name = str(dev)
            print(dev_name)
            self.combo_device.addItem(dev_name)

        if self.combo_device.count():
            self.combo_device.setPlaceholderText("Select your Lunii")

            # automatic select if only one device
            if self.combo_device.count() == 1:
                self.combo_device.setCurrentIndex(0)
        else:
            self.combo_device.setPlaceholderText("No Lunii detected :(")
        self.combo_device.addItem("C:/Work/reverse/Lunii.RE/tools/lunii-packs/test/_v2/")
        self.combo_device.addItem("C:/Work/reverse/Lunii.RE/tools/lunii-packs/test/_v3/")

    def cb_dev_select(self):
        # getting current device
        dev_name = self.combo_device.currentText()

        if dev_name:
            self.lunii_device = LuniiDevice(dev_name)
            if self.lunii_device.lunii_version == LUNII_V2:
                self.lbl_version.setText("v2")
            elif self.lunii_device.lunii_version == LUNII_V3:
                self.lbl_version.setText("v3")
            self.ts_update()

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
            one_story_imageURL = story_pict(uuid)

            # nothing to display
            if (not one_story_desc or one_story_desc == DESC_NOT_FOUND) and not one_story_imageURL:
                self.te_story_details.setVisible(False)
                self.lbl_picture.setVisible(False)
                return

            # Update story description
            self.te_story_details.setText(one_story_desc)

            # Fetch image from URL and display
            try:
                # Set the timeout for the request
                response = requests.get(one_story_imageURL, timeout=1)
                if response.status_code == 200:
                    # Load image from bytes
                    image_data = response.content
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_data)

                    scaled_pixmap = pixmap.scaled(192, 192, aspectMode=Qt.KeepAspectRatio, mode=Qt.SmoothTransformation)
                    self.lbl_picture.setPixmap(scaled_pixmap)
                else:
                    self.lbl_picture.setText("Failed to fetch BMP file.")

            except requests.exceptions.Timeout:
                self.lbl_picture.setText("Failed to fetch BMP file.")

            except requests.exceptions.RequestException as e:
                self.lbl_picture.setText("Failed to fetch BMP file.")

    def ts_update(self):
        # clear previous story list
        self.tree_stories.clear()
        self.ts_populate()
        # update status in status bar
        self.sb_update_summary()

        # clean progress bars
        self.lbl_total.setVisible(False)
        self.pbar_total.setVisible(False)
        self.lbl_story.setVisible(False)
        self.pbar_story.setVisible(False)

    def ts_populate(self):
        # empty device
        if self.lunii_device.stories is None or len(self.lunii_device.stories) == 0:
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

    def sb_update_summary(self):
        # displayed items
        count_items = self.tree_stories.topLevelItemCount()

        sb_message = f" {count_items}/{len(self.lunii_device.stories)}"
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

        # preparing validation window
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete stories")
        message = "You are requesting to delete : \n"
        for item in selection:
            message += f"- {item.text(COL_NAME)}\n"
        message += "\nDo you want to proceed ?"
        dlg.setText(message)
        dlg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        dlg.setIcon(QMessageBox.Warning)
        button = dlg.exec_()

        if button != QMessageBox.Ok:
            return

        self.pbar_total.setVisible(True)
        self.pbar_total.setRange(0, len(selection))
        self.lbl_total.setVisible(True)

        # processing selection
        for index, item in enumerate(selection):
            self.pbar_total.setValue(index)
            # remove UUID from pi file
            uuid = item.text(COL_UUID)
            # remove story contents from device
            self.lunii_device.remove_story(uuid)

        # refresh stories
        self.ts_update()

    def ts_export(self):
        print("ts_export")
        self.pbar_total.setVisible(True)

        # getting selection
        selection = self.tree_stories.selectedItems()
        if len(selection) == 0:
            return

        # depending on how many files selected
        if len(selection) == -1:
            # save one file only

            # TODO : review output filename

            # preparing filename
            save_fn = f"{selection[0].text(COL_NAME)}.({selection[0].text(COL_UUID)[-8:]}).plain.pk"

            # creating dialog box
            filename = QFileDialog.getSaveFileName(self, "Save Story", save_fn, "Plain pk files (*.plain.pk)")
            print(filename)

            # TODO: Save current file
        else:
            # picking an output directory
            out_dir = QFileDialog.getExistingDirectory(self, "Ouput Directory for Stories", "",
                                                       QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
            print(out_dir)

            # Save all files
            for item in selection:
                self.lunii_device.export_story(item.text(COL_UUID), out_dir)

        self.pbar_total.setVisible(False)

    def ts_import(self):
        print("ts_import")
        self.pbar_total.setVisible(True)
        self.pbar_total.setValue(0)

        if not self.lunii_device:
            return

        file_filter = "PK files (*.plain.pk *.pk);;Archive files (*.7z *.zip);;All supported (*.pk *.7z *.zip);;All files (*)"
        filename, _ = QFileDialog.getOpenFileName(self, "Open Stories", "", file_filter)

        if not filename:
            self.pbar_total.setVisible(False)
            return

        # importing selected files
        print(filename)
        self.lunii_device.import_story(filename)

        # refresh stories
        self.ts_update()

    def slot_zip_progress(self, message, progress):
        # handling progress bar
        if not self.pbar_total.isVisible() and progress != 100:
            self.pbar_total.setVisible(True)

        if progress >= 100:
            self.pbar_total.setVisible(False)

        # putting message
        self.statusbar.showMessage(message)

    def ts_dragenter_action(self, event):
        print("Drag Enter")

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
        print("Drop")
        # getting path for dropped files
        file_paths = [url.toLocalFile() for url in event.mimeData().urls()]

        # updating UI for progress
        self.lbl_total.setVisible(True)
        self.pbar_total.setVisible(True)
        self.pbar_total.setValue(0)
        self.pbar_total.setRange(0, len(file_paths))
        self.lbl_story.setVisible(True)
        self.pbar_story.setVisible(True)

        # importing selected files
        for index, file in enumerate(file_paths):
            self.pbar_total.setValue(index)
            self.lunii_device.import_story(file)

        # refresh stories
        self.ts_update()

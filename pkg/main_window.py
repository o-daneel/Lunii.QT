from pathlib import WindowsPath
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem
from PySide6.QtGui import QFont
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

        # Connect the context menu
        # self.tw_assets.setContextMenuPolicy(QtCore.Qt.Cus)
        # self.tw_assets.customContextMenuRequested.connect(self.tw_context_menu)
        pass

    # connecting slots and signals
    def setup_connections(self):
        self.combo_device.currentIndexChanged.connect(self.cb_dev_select)
        self.le_filter.textChanged.connect(self.ts_update)

    # WIDGETS UPDATES
    def cb_dev_refresh(self):
        dev_list = find_devices()
        self.combo_device.clear()

        dev : WindowsPath
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
            item.setText(0, story_name(story))
            item.setText(1, str(story).upper())
            item.setFont(1, console_font);
            self.tree_stories.addTopLevelItem(item)

    def sb_update_summary(self):
        # displayed items
        count_items = self.tree_stories.topLevelItemCount()

        self.sb_message = f" {count_items}/{len(self.stories)}"
        self.statusbar.showMessage(self.sb_message)

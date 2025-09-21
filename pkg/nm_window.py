from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from pkg.api.constants import LUNII_CFGPOS_NM_AUTOPLAY, LUNII_CFGPOS_NM_ENABLED, LUNII_CFGPOS_NM_ENABLED, LUNII_CFGPOS_NM_STORYCOUNT, LUNII_CFGPOS_NM_TURNOFF_NM, LUNII_CFGPOS_NM_VOL_LIMIT
from pkg.api.device_lunii import LuniiDevice
from pkg.ui.nm_ui import Ui_nightMode

class NightModeWindow(QDialog, Ui_nightMode):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        Ui_nightMode.__init__(self)

        # internal variables
        self.audio_device: LuniiDevice = None

        # UI init
        self.init_ui()

    def init_ui(self):
        self.setupUi(self)
        self.modify_widgets()
        self.setup_connections()

    # update ui elements state (enable, disable, context enu)
    def modify_widgets(self):
        self.iconLunii = QIcon(":/icon/res/lunii.ico")
        self.setWindowIcon(self.iconLunii)

        self.remove_audioDevice()

    # connecting slots and signals
    def setup_connections(self):
        self.btn_save.clicked.connect(self.accept)

        self.lbl_enable.mousePressEvent = lambda event: self.cbox_enable.click() if event.button() == Qt.MouseButton.LeftButton else None
        self.cbox_enable.clicked.connect(self.cb_nm_enable)
        
        self.lbl_limit.mousePressEvent = lambda event: self.cbox_limit.click() if event.button() == Qt.MouseButton.LeftButton else None
        self.cbox_limit.clicked.connect(self.cb_limit)

        self.lbl_autoplay.mousePressEvent = lambda event: self.cbox_autoplay.click() if event.button() == Qt.MouseButton.LeftButton else None
        self.cbox_autoplay.clicked.connect(self.cb_autoplay)
        
        self.lbl_turnoff.mousePressEvent = lambda event: self.cbox_turnoff_nm.click() if event.button() == Qt.MouseButton.LeftButton else None
        self.cbox_turnoff_nm.clicked.connect(self.cb_tunoff)

    @property
    def config(self):
        new_config = list(self.audio_device.config)
        # updating config with current window widget
        new_config[LUNII_CFGPOS_NM_ENABLED] = 1 if self.cbox_enable.checkState() == Qt.CheckState.Checked else 0
        new_config[LUNII_CFGPOS_NM_VOL_LIMIT] = 30 if self.cbox_limit.checkState() == Qt.CheckState.Checked else 0
        new_config[LUNII_CFGPOS_NM_AUTOPLAY] = 1 if self.cbox_autoplay.checkState() == Qt.CheckState.Checked else 0
        new_config[LUNII_CFGPOS_NM_STORYCOUNT] = self.sbox_maxstories.value()
        new_config[LUNII_CFGPOS_NM_TURNOFF_NM] = 1 if self.cbox_turnoff_nm.checkState() == Qt.CheckState.Checked else 0

        return new_config

    def remove_audioDevice(self):
        self.audio_device = None

        # if none, disable all
        self.groupBox.setDisabled(True)

    def set_audioDevice(self, device):
        self.audio_device = device

        # applies config from audio device
        # if none, disable all
        self.groupBox.setDisabled(self.audio_device == None)

        if self.audio_device:
            # updating enabled mode
            self.cbox_enable.setChecked(self.audio_device.config[LUNII_CFGPOS_NM_ENABLED] != 0)
            self.cbox_limit.setChecked(self.audio_device.config[LUNII_CFGPOS_NM_VOL_LIMIT] != 0)
            self.cbox_autoplay.setChecked(self.audio_device.config[LUNII_CFGPOS_NM_AUTOPLAY] != 0)
            self.sbox_maxstories.setValue(self.audio_device.config[LUNII_CFGPOS_NM_STORYCOUNT])
            self.cbox_turnoff_nm.setChecked(self.audio_device.config[LUNII_CFGPOS_NM_TURNOFF_NM] != 0)
        
        # propagate new state to all widgets
        self.cb_nm_enable()

    def cb_nm_enable(self):
        nm_enabled = self.cbox_enable.checkState() == Qt.CheckState.Checked

        # propagate nm mode to all elements
        self.audio_device.config[LUNII_CFGPOS_NM_ENABLED] = nm_enabled
        # limit section
        self.cbox_limit.setEnabled(nm_enabled)
        self.cb_limit()
        # autoplay section
        self.cbox_autoplay.setEnabled(nm_enabled)
        self.cb_autoplay()
        # turnoff section
        self.cbox_turnoff_nm.setEnabled(nm_enabled)
        self.cb_tunoff()

    def cb_limit(self):
        nm_enabled = self.cbox_enable.checkState() == Qt.CheckState.Checked
        limit_enabled = self.cbox_limit.checkState() == Qt.CheckState.Checked and \
                        self.cbox_enable.checkState() == Qt.CheckState.Checked

        # limit section
        self.lbl_limit.setEnabled(nm_enabled)
        self.lbl_desc_limit.setEnabled(limit_enabled)
        
    def cb_autoplay(self):
        nm_enabled = self.cbox_enable.checkState() == Qt.CheckState.Checked
        autoplay_enabled = self.cbox_autoplay.checkState() == Qt.CheckState.Checked and \
                           self.cbox_enable.checkState() == Qt.CheckState.Checked

        # autoplay section
        self.lbl_autoplay.setEnabled(nm_enabled)
        self.lbl_desc_autoplay.setEnabled(autoplay_enabled)
        self.lbl_maxstories.setEnabled(autoplay_enabled)
        self.sbox_maxstories.setEnabled(autoplay_enabled)

    def cb_tunoff(self):
        nm_enabled = self.cbox_enable.checkState() == Qt.CheckState.Checked
        turnoff_enabled = self.cbox_turnoff_nm.checkState() == Qt.CheckState.Checked and \
                          self.cbox_enable.checkState() == Qt.CheckState.Checked

        # turnoff section
        self.lbl_turnoff.setEnabled(nm_enabled)
        self.lbl_desc_turnoff.setEnabled(turnoff_enabled)
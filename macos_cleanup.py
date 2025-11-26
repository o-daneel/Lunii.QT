import os, shutil, subprocess
import glob

APP_PATH = "dist/luniiQt.app/Contents"

def remove(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

# Remove unneeded frameworks with wildcard support
framework_patterns = [
    "Assistant.app",
    "Designer.app",
    "Linguist.app",
    "QtPdf.*",
    "QtWebEngineCore.*",
    "QtWebEngineWidgets.*",
    "QtMultimedia.*",
    "Qt3D*.*",
    "Qt/lib/Qt3D*.framework",
    "Qt/lib/QtBluetooth.framework",
    "Qt/lib/QtCharts*.framework",
    "Qt/lib/QtDesigner*.framework",
    "Qt/lib/QtGraph*.framework",
    "Qt/lib/QtLabs*.framework",
    "Qt/lib/QtMultimedia.framework",
    "Qt/lib/QtOpenGL*.framework",
    "Qt/lib/QtP*.framework",
    "Qt/lib/QtQuickC?*.framework",
    "Qt/lib/QtSql*.framework",
    "Qt/lib/QtWebEngine*.framework",
    "Qt/translations/assistant*",
    "Qt/translations/designer*",
    "Qt/translations/linguist*",
    "Qt/translations/qtdecl*",
    "Qt/translations/qt_help*",
    "Qt/plugins/designer*",
    "Qt/plugins/qml*",
    "Qt/qml",
]
frameworks_dir = os.path.join(APP_PATH, "Resources/lib/python3.11/PySide6")
for pattern in framework_patterns:
    for fw_path in glob.glob(os.path.join(frameworks_dir, pattern)):
        remove(fw_path)

# # Keep only minimal plugins
# keep_plugins = {"libqcocoa.dylib", "libqico.dylib", "libqjpeg.dylib"}
# plugins_dir = os.path.join(APP_PATH, "PlugIns")
# for root, _, files in os.walk(plugins_dir):
#     for f in files:
#         if f not in keep_plugins:
#             os.remove(os.path.join(root, f))

# # Remove translations
# remove(os.path.join(APP_PATH, "Resources", "translations"))

# Strip binaries
subprocess.call("find dist/luniiQt.app -type f -perm +111 -exec strip {} \\;", shell=True)

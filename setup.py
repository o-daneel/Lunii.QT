import os
import sys
from pkg.main_window import APP_VERSION
from cx_Freeze import Executable, setup

# base="Win32GUI" should be used only for Windows GUI app
base = "Win32GUI" if sys.platform == "win32" else None

directory_table = [
    ("ProgramMenuFolder", "TARGETDIR", "."),
    ("Lunii", "ProgramMenuFolder", "Lunii QT"),
]

shortcut_table = [
    ("DesktopShortcut",        # Shortcut
     "DesktopFolder",          # Directory_
     "Lunii Qt",               # Name that will be show on the link
     "TARGETDIR",              # Component_
     "[TARGETDIR]Lunii-Qt.exe",# Target exe to exexute
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
    ),
    ("StartupShortcut",        # Shortcut
     "StartMenuFolder",        # Directory_
     "Lunii Qt",               # Name that will be show on the link
     "TARGETDIR",              # Component_
     "[TARGETDIR]Lunii-Qt.exe",# Target exe to exexute
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
    ),
]

msi_data = {
    "Directory": directory_table,
    "ProgId": [
        ("Prog.Id", None, None, "A simple GUI to manage your Lunii/Flam storytellers", "IconId", None),
    ],
    # "Icon": [
    #     ("IconId", "./res/lunii.ico"),
    # ],
    "Shortcut": shortcut_table
}

bdist_msi_options = {
    'skip_build': True,
    # "all_users": True,
    "data": msi_data,
    "upgrade_code": "{563b928d-6693-4028-9388-e2b1616648fe}",
    # "add_to_path": True,
}

options = {
    "build_exe": {
        "bin_excludes": ["libqpdf.so", "libqpdf.dylib"],
        # exclude packages that are not really needed
        "excludes": [
            "tkinter",
            "unittest",
            # "email",
            # "http",
            "xml",
            "pydoc",
        ],
        "include_files" : ["tools/ffmpeg.exe"],
        "zip_include_packages": ["PySide6", "shiboken6"],
        "silent_level": "1",
        "include_msvcr": True
    },
    "bdist_msi": bdist_msi_options
    # "bdist_mac": {
    #     "custom_info_plist": None,  # Set this to use a custom info.plist file
    #     "codesign_entitlements": os.path.join(
    #         os.path.dirname(__file__), "codesign-entitlements.plist"
    #     ),
    #     "codesign_identity": None,  # Set this to enable signing with custom identity (replaces adhoc signature)
    #     "codesign_options": "runtime",  # Ensure codesign uses 'hardened runtime'
    #     "codesign_verify": False,  # Enable to get more verbose logging regarding codesign
    #     "spctl_assess": False,  # Enable to get more verbose logging regarding codesign
    # },
}

executables = [
    Executable(
        "lunii-qt.py",
        # icon="./res/lunii.ico",
        target_name="Lunii-Qt",
        base=base,
        # shortcut_name="Lunii QT",
        # shortcut_dir="DesktopFolder",
    )
]

setup(
    name="Lunii Qt",
    version=APP_VERSION,
    description="A simple GUI to manage your Lunii/Flam storytellers",
    author="o.Daneel",
    options=options,
    executables=executables,
)
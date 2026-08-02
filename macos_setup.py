from setuptools import setup

APP = ['lunii-qt.py']
DATA_FILES = ['res/lunii.ico', 'res/dmg_icon.icns']
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'res/dmg_icon.icns',
    'plist': {
        'CFBundleName': 'luniiQt',
        'CFBundleDisplayName': 'Lunii Qt',
        'CFBundleIdentifier': 'com.o-daneel.luniiqt',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleExecutable': 'lunii-qt',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'CFBundleDevelopmentRegion': 'English',
        'CFBundleDocumentTypes': [],
    },
    # Copied wholesale rather than byte-compiled into the zip:
    #  - charset_normalizer is imported lazily by requests, so py2app's dependency
    #    scan misses it and every startup warns "Unable to find acceptable character
    #    detection dependency". (The CI install also forces the pure-Python build --
    #    the mypyc wheel needs a hash-named top-level module py2app cannot see.)
    #  - backports is a namespace package, and setuptools vendors a backports.tarfile
    #    whose __init__ shadows it in the zip. backports.zstd (py7zr -> pyzstd) then
    #    goes missing and the app dies at startup on 'cannot import name zstd'.
    'packages': ['PySide6', 'shiboken6', 'charset_normalizer', 'backports', 'pyzstd'],
    'excludes': ['tkinter', 'pytest', 'unittest', 'sqlite3'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

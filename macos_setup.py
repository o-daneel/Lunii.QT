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
    'packages': ['PySide6', 'shiboken6'],
    'excludes': ['tkinter', 'pytest', 'unittest', 'sqlite3'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

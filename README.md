# Lunii.QT
A Python QT app to manage Lunii Storyteller (supporting v1, v2 and v3)  
(compatibility with STUdio archive to come soon)

![Main Window](./res/screenshot.png)

## Shortcuts

| Keys       | Actions                        |
|------------|--------------------------------|
| "Alt+Up"   | Move the selected item(s) Up   |
| "Alt+Down" | Move the selected item(s) Down |
| "Delete"   | Remove the selected item(s)    |
| "Ctrl+S"   | Export the selection           |
| "Ctrl+I"   | Import new story               |
| "F5"       | Refresh devices                |

## TODO
* add button for official db refresh
* fecth studio db
* support studio stories
* add picture to tree list
* ~~add FW version~~
* ~~improve story move up/down~~
* ~~save new story order on lunii~~
* ~~improve lunii detection for Linux/MacOs~~
* ~~check for v3 keys for export~~
* ~~more debug messages~~ 
* ~~Create dedicated thread & slots to avoid interface freeze during import/export~~
* ~~support Linux / Mac (path entry)~~


## HowTo

### Prepare env

Prepare a Vitrual environment for your project and install requirements
```
$ python -m venv venv
```

Switch to your venv 
* on Linux   
   `$ source venv/bin/activate`
* on Windows   
  `$ .\venv\Scripts\activate.bat`

Install dependencies
```
$ python -m pip install -r requirements.txt
```
or
```
$ pip install -r requirements.txt
```

### Build UI files
```
$ pyside6-uic src/ui/main.ui -o src/ui/main_ui.py
$ pyside6-rcc resources.qrc -o resources_rc.py
```
### Run
```
$ python lunii-Qt.py
```

### Build GUI executable
```
$ pip install pyinstaller
$ pyinstaller lunii-qt.spec
...
$ dist\lunii-qt
```

## Trick
### Cache management
This application will download once for all the official story database and any request pictures to the application dedicated folder
* `%HOME%.lunii-qt\official.db`
* `%HOME%.lunii-qt\cache\*`

In case of any trouble, just remove this file and directory to force refresh

### V3 export
In order to suport story export from Lunii v3 hardware, you must place your device keys in here :
```bash
%HOME%\.lunii-qt\v3.keys
$HOME/.lunii-qt/v3.keys
```
It is a binary file with 0x10 bytes for Key and 0x10 bytes for IV
### ICO creation
```bash
magick convert logo.png -define icon:auto-resize="256,128,96,64,48,32,16"  logo.ico
```

## Credits
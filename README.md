# Lunii.QT
A Python QT app to manage Lunii Storyteller, including **reorder** / **import** / **export**   

### Hardware supported:
* **v1, v2**  (full Support)
* **v3**  (export requires device key file)  

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
* fecth STUdio db
* support studio stories
* add picture to tree list
* dedicated menu to allow story details
* config file to backup menu config (sizes / details)
* ~~Move Top / Bottom, Export All to be implemented~~
* ~~selection lost on key up / down after move~~
* ~~display story size~~
* ~~Add menu File / Tools / About~~
  * ~~File : Move Up, Move Down, Import, Export, Export All, Quit~~
  * ~~Tools : Check Update / Get current FW / Story Sizes / (Refresh Official DB)~~
* ~~add button for official db refresh~~
* ~~fix Lunii v1 key issue~~
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
Thanks to :
* **olup** for STUdio archive format 
* **sniperflo** for v1 support & debug 

# Links / Similar repos
* [Lunii v3 - Reverse Engineering](https://github.com/o-daneel/Lunii_v3.RE)
* [STUdio - Story Teller Unleashed](https://marian-m12l.github.io/studio-website/)
* [(GitHub) STUdio, Story Teller Unleashed](https://github.com/marian-m12l/studio)
* [Lunii Admin](https://github.com/olup/lunii-admin) (a GO implementation of a STUdio alternative)
* [Lunii Admin Web](https://github.com/olup/lunii-admin) (same as previous but from a browser)

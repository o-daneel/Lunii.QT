![Total downloads](https://img.shields.io/github/downloads/o-daneel/Lunii.QT/total?label=Total%20Downloads)
[![luniiQt v3.1.0](https://img.shields.io/github/downloads/o-daneel/Lunii.QT/v3.1.0/total?label=luniiQt%20v3.1.0)](https://github.com/o-daneel/Lunii.QT/releases/tag/v3.1.0)
[![luniiQt v3.0.0](https://img.shields.io/github/downloads/o-daneel/Lunii.QT/v3.0.0/total?label=luniiQt%20v3.0.0)](https://github.com/o-daneel/Lunii.QT/releases/tag/v3.0.0)
[![luniiQt v2.7.6](https://img.shields.io/github/downloads/o-daneel/Lunii.QT/v2.7.6/total?label=luniiQt%20v2.7.6)](https://github.com/o-daneel/Lunii.QT/releases/tag/v2.7.6)

:fr: [README en français](README.md) :fr:

# Lunii.QT
A Python QT app to manage <u>Lunii</u> and <u>Flam</u> Storytellers, including **reorder** / **import** / **export** / **hide** / **firmware download**   
for Windows / Linux / macOS  
(compatible with STUdio archive, **with** transcoding)

> **FAQ :** Please refer to already asked questions on [Discussions](https://github.com/o-daneel/Lunii.QT/discussions) section, or refer to revelant [Issues](https://github.com/o-daneel/Lunii.QT/issues?q=is%3Aissue%20label%3A%22good%20first%20issue%22)

# Breaking news
* 😎 **Flam support** 😎  
The application now allows importing Lunii stories onto your Flam, provided it is running firmware v2.x.x.  
   > **Warning:** the Flam is VERY slow over USB. Please be patient. (around 4min for 80MB)

* 😎 **Lunii v3 & Firmware 3.2.x** 😎  
Lunii.QT has been updated to support the latest firmware (3.2.2 and later). Thanks to a longer analysis (I should have spent 10 more minutes at the first sight to connect neurons), **a stable** and **VERY simple** workaround has been found.  
Forget about all previous .md and firmware recommendations.
   > **Reminder:** Keep your v3 Firmware files safe (you can always downgrade) and keep away from automatic upgrades

### Hardware supported:
* **v1, v2**  (full Support)
* **v3**  (v6 and v7 md files supported 💪🏻, personal backup only)  
* **Flam** (full Support, personal backup only)

### Limitations
* Application <u>no longer</u> allows Lunii Official stories to be exported (due to piracy)  
  Flam devices <u>can</u> back up and restore their stories, but they will only work on the original device.
* Audio transcoding requires FFMPEG v6 to be present ([more details](#audio-transcoding))

### Table of contents
<!-- TOC -->
- [Lunii.QT](#luniiqt)
  - [User Interface](#user-interface)
    - [Main window](#main-window)
    - [Night mode](#night-mode)
  - [Shortcuts](#shortcuts)
  - [Features](#features)
  - [Audio Transcoding](#audio-transcoding)
  - [Firmware upgrade](#firmware-upgrade)
  - [Supported archive formats (Lunii)](#supported-archive-formats-lunii)
  - [Python ? HowTo](#python--howto)
    - [Prepare env](#prepare-env)
    - [Build UI files](#build-ui-files)
    - [Build Translation files](#build-translation-files)
    - [Build UI files](#build-ui-files-1)
    - [Run](#run)
    - [Build GUI executable](#build-gui-executable)
  - [Tricks](#tricks)
    - [macOS - Application Authorization](#macos---application-authorization)
    - [Third Party story metadata](#third-party-story-metadata)
    - [Cache management](#cache-management)
    - [Linux missing dependencies](#linux-missing-dependencies)
    - [v3 export](#v3-export)
    - [ICO creation](#ico-creation)
  - [Credits](#credits)
- [Links / Similar repos](#links--similar-repos)
<!-- TOC -->


## User Interface

<img src="./res/screenshot_about.png" width="450"><br>  
  
<img src="./res/screenshot_main.png" width="600"><br>    
<img src="./res/screenshot_nm_off.png" width="300"><img src="./res/screenshot_nm_on.png" width="300"><br>  
<img src="./res/screenshot_debug.png" width="600"> 

### Main window

<img src="./res/screenshot_interface.png" width="600">  

1. The **menu bar**. It will notify you when an update is available  
   (just get it with Menu About/Update to v2.X.X)
2. The **location of your Lunii/Flam** when it's connected.   
   The button on the left updates automatic detection.
3. Configuring **Night mode** ([here](#night-mode))
4. **Official DB refresh** : Updates the list of stories and related information from the official Lunii Store. Use it when some official are not recognized.
5. The **list of your stories** with UUID and Database (DB) origin.  
   The UUID: This unique identifier allows you to associate stories with their folder on the Lunii, thanks to the last eight characters that make up the name of the folder associated with that story.

   * **DB** stands for **Database**. This application supports two different databases
     - **O** - Lunii **O**fficial Database  
        _(all metadata are fed from Lunii servers)_
     - **T** - **T**hirdparty Database, also known as Unofficial or Custom Stories  
        _(Those metadata can't be fetched. They are completed upon story import)_

6. The 🛏️ icon indicates that **the story supports Night Mode**. You can force this status from the context menu.

7. **Hidden stories** (the greyed-out entries in the list).  
   This feature can be activated via the context menu on a story.  
   It has two uses:  
   1. Hide certain stories to prevent the child from spending too much time choosing a story at night. This avoids having to delete and copy them again later.  
   2. Prevent the deletion of unofficial stories during synchronization with the Luniistore application. Hidden stories are still physically present on the device, but will not be visible to Luniistore. Don't forget to "hide" your stories before clicking "synchronize"!

8. The **status bar**, you'll find 
   * your SNU (serial number)
   * the firmware version of your Lunii/Flam
   * the available space  
   * the number of stories it contains

### Night mode
<img src="./res/screenshot_nm_off.png" width="300"><img src="./res/screenshot_nm_on.png" width="300">  

## Shortcuts

| Keys           | Actions                          |
|----------------|----------------------------------|
| `Ctrl+Up`      | Move the selected item(s) Top    |
| `Alt+Up`       | Move the selected item(s) Up     |
| `Alt+Down`     | Move the selected item(s) Down   |
| `Ctrl+Down`    | Move the selected item(s) Bottom |
|                |                                  |
| `Ctrl+I`       | Import new story                 |
| `Ctrl+S`       | Export the selection             |
| `Ctrl+Shift+S` | Export all the stories           |
| `Ctrl+H`       | Hide/Show selected stories       |
| `Ctrl+N`       | Force NightMode on stories       |
| `Delete`       | Remove the selected item(s)      |
|                |                                  |
| `Ctrl+O`       | Open a Lunii/Flam device         |
| `Ctrl+L`       | Open debug log window            |
| `Ctrl+Q`       | Exit the application             |
| `F1`           | About the app                    |
| `F5`           | Refresh devices                  |

## Features
* Automatic **Update** detection
* **Import** / **Export** / **Remove** stories
* Support **STUdio** archive formats, and **import STUdio database**
* **Reorganize** the stories in the order you want
* **Hide** stories  
  In order to avoid stories to get removed by Luniistore PC Synchronization, you can temporary hide them (all files ares kept on device), sync, and revert hide.
* **Lost Stories**  
  Three tools are offered to manage "crashed" stories on your device.   
 ![](./res/screenshot_lost.png)
  You can :
  * List them  
  _(app will try to fix broken stories, in particular auth files on v1/v2)_
  * Recover them (if they are complete)
  * Remove them (**be careful, files will be deleted**)  
* **Get Firmware**  for your device (refer [this section](#firmware-upgrade))

## Audio Transcoding
Some third-party stories are using non MP3 files. Thus they can't be installed as it is on Lunii. It requires a **transcoding** step. This extra process is done using **FFMPEG** tool ( [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) )

**WARNING** : transcoding is <u>very long</u>, you should be patient. That's why you should prefer the [.plain.pk](#plainpk) format that use compatible audio.

### Installation
#### Windows

**NOTE :** By default, from now on, the Windows portable and MSI will embed FFMPEG 6.1.1   
  
Procedure:
1) grab your ffmpeg release from [here](https://www.gyan.dev/ffmpeg/builds/)
2) rename it to `ffmpeg.exe`
3) copy beside lunii-qt.exe   
    ```
    - 
     |- lunii-qt.exe
     |- ffmpeg.exe
    ```
4) restart luni-qt

Alternate method (I prefer):
1) open powershell terminal
2) run the following commands to install Scoop Package manager  
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
    ```
3) install ffmpeg with   
  `scoop install ffmpeg`
4) restart luni-qt

#### Linux
1) open a terminal
2) run following command :   
`sudo apt-get install ffmpeg`
4) restart luni-qt

#### macOS
To ease ffmpeg tool installation, it is recommended to use Brew from https://brew.sh/  
1) open a terminal
2) copy and paste the following link  
`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
3) At the end of the installation, type into the terminal:  
`brew install ffmpeg`
4) restart luni-qt


### Checking 
Within the application, the Tools menu will display the status of detection.
#### Not found
![Not available](res/ffmpeg_off.png)  
#### Found
![Available](./res/ffmpeg_on.png)


## Firmware upgrade

Lunii.QT offers you the possibility to backup and upgrade your Firmware without connecting to LuniiStore (you won't lost your non official loaded stories). This procedure is experimental but so far no one faced issues.

**NOTE 1:** Remember to keep a backup of your firmware for Lunii v3 and FLAMs, in cas of a release that would break to third party stories trick. <u>You will be able to downgrade.</u>  
**NOTE 2:** You cannot choose the firmware version. You'll only get the latest available from Lunii servers.


### HowTo - Lunii
1. Select a Lunii/Flam device
2. Menu **Tools/Get FW Update**
3. You'll be prompted for login entry  
<img src="./res/screenshot_login.png" width="170">

4. Enter your Luniistore credentials (they are not saved for security purpose).  
   You can verify this point here
   https://github.com/o-daneel/Lunii.QT/blob/a8bd30e1864552687f235004085a417d7c6b00e6/pkg/main_window.py#L468-L475
5. Pick a location where to save your firmware(s) (there are two for Lunii v1)
6. Copy it to the root dir of your device
7. Rename it to `fa.bin` (and optionnally  `fu.bin` for Lunii v1)   
```
- 
 |- .contents
 |- .md
 |- .pi
 |- fa.bin
 |- ... (other files)
```
8. Power OFF, Power ON, Wait : **TADA**  
   (if you reconnect your lunii on your pc, the `fa.bin` should have been removed)


### HowTo - Flam
1. Select a Flam device
2. Menu **Tools/Get FW** Update
3. You'll be prompted for login entry  
<img src="./res/screenshot_login.png" width="170">

4. Enter your Luniistore credentials (they are not saved for security purpose).  
   You can verify this point here
   https://github.com/o-daneel/Lunii.QT/blob/a8bd30e1864552687f235004085a417d7c6b00e6/pkg/main_window.py#L468-L475
5. Pick a location where to save your firmwares (`update-main.enc` and `update-comm.enc`)
6. Copy them to the root dir of your device   
```
- 
 |- etc/
 |- str/
 |- .mdf
 |- update-main.enc
 |- update-comm.enc
 |- ... (other files)
```
7. Create an empty file `cable_update_complete` in /tmp
```
- 
 |- etc/
 |- str/
 |- .mdf
 |- update-main.enc
 |- update-comm.enc
 |- tmp/
   |- cable_update_complete
 |- ... (other files)
```
8. Eject USB from Flam device (USB cable must be kept connected) and update process will start : **TADA**  
   (if you reconnect your flam on your pc, the `*.enc` should have been removed)

## Supported archive formats
### for Lunii
#### .plain.pk
**Filename** :  `story_name.8B_UUID.plain.pk`  
**Ciphering** : None / Plain  
**Structure** :  

      _thumbnail.png
      _metadata.json
      uuid.bin
      ni
      li.plain
      ri.plain
      si.plain
      rf/000/XXYYXXYY.bmp
      sf/000/XXYYXXYY.mp3

#### .v1.pk / .v2.pk
**Filename** :  
* `LONG_UUID.v2.pk`  
* `LONG_UUID.v2.pk`  
* `LONG_UUID.pk`  
  
**Ciphering** : Generic Key  
**Structure** :  

      00000000000000000000000000000000/ni
      00000000000000000000000000000000/li
      00000000000000000000000000000000/ri
      00000000000000000000000000000000/si
      00000000000000000000000000000000/rf/000/XXYYXXYY
      00000000000000000000000000000000/sf/000/XXYYXXYY

#### ZIP (old Lunii.QT)
**Filename** :  `8B_UUID - story_name.zip`  
**Ciphering** : Generic Key  
**Structure** :  

      uuid.bin
      ni
      li
      ri
      si
      rf/000/XXYYXXYY
      sf/000/XXYYXXYY

#### ZIP (alternate)
**Filename** :  `AGE+] story_title DASHED_UUID.zip`  
**Ciphering** : Generic Key  
**Structure** : (same as [.v1.pk / .v2.pk](#v1pk--v2pk))

      00000000-0000-0000-0000-000000000000/ni
      00000000-0000-0000-0000-000000000000/li
      00000000-0000-0000-0000-000000000000/ri
      00000000-0000-0000-0000-000000000000/si
      00000000-0000-0000-0000-000000000000/rf/000/XXYYXXYY
      00000000-0000-0000-0000-000000000000/sf/000/XXYYXXYY

#### 7z
**Filename** : `AGE+] story_title DASHED_UUID.7z`  
**Ciphering** : Generic Key  
**Structure** :  

      00000000-0000-0000-0000-000000000000/ni
      00000000-0000-0000-0000-000000000000/li
      00000000-0000-0000-0000-000000000000/ri
      00000000-0000-0000-0000-000000000000/si
      00000000-0000-0000-0000-000000000000/rf/000/XXYYXXYY
      00000000-0000-0000-0000-000000000000/sf/000/XXYYXXYY

#### STUdio (ZIP / 7z)
**Filename** : `AGE+] story_title DASHED_UUID.zip .7z`  
**Ciphering** : None  

**Structure** :  

        assets/
        story.json
        thumbnail.png
      
### for Flam
**NOTE :** The Flam story format is still unknown. Only personal backup are supported.
#### .zip
**Filename** :  `story_name.8B_UUID.zip`  
**Ciphering** : Story Key (unknown)  
**Structure** :  

      00000000-0000-0000-0000-000000000000/info
      00000000-0000-0000-0000-000000000000/main.lsf
      00000000-0000-0000-0000-000000000000/version
      00000000-0000-0000-0000-000000000000/key
      00000000-0000-0000-0000-000000000000/img/*.lif
      00000000-0000-0000-0000-000000000000/img/script/*.lif
      00000000-0000-0000-0000-000000000000/script/*.lsf
      00000000-0000-0000-0000-000000000000/sounds/*.mp3
      00000000-0000-0000-0000-000000000000/sounds/*.mp3map

## Python ? HowTo

### Prepare env

First, clone the git repo   
Prepare a Virtual environment for your project and install requirements
```bash
$ python3 -m venv venv
```

Switch to your venv 
* on Linux   
   `source venv/bin/activate`
* on Windows   
  `.\venv\Scripts\activate.bat`

Install dependencies
```
$ pip install -r requirements.txt
```

**Linux** has one more extra dependency to be installed  

```bash
$ apt install libxcb-cursor0
```
### Build UI files
```bash
$ pyside6-uic pkg/ui/main.ui -o pkg/ui/main_ui.py
$ pyside6-uic pkg/ui/nm.ui   -o pkg/ui/nm_ui.py
```
### Build Translation files
```bash
$ pyside6-lupdate ./pkg/ui/main.ui ./pkg/ui/nm.ui ./pkg/ui/about_ui.py ./pkg/ui/debug_ui.py ./pkg/ui/login_ui.py ./pkg/nm_window.py ./pkg/main_window.py ./pkg/ierWorker.py ./pkg/versionWorker.py ./pkg/api/devices.py -ts ./locales/fr_FR.ts
$ pyside6-linguist ./locales/fr_FR.ts  # optionnaly, update translations
$ pyside6-lrelease ./locales/fr_FR.ts ./locales/fr_FR.qm  
```
### Build resource files
```bash
$ pyside6-rcc resources.qrc -o resources_rc.py
```
### Run
```bash
$ python lunii-qt.py
```

### Build GUI executable
**NOTE :** PyInstaller by its design generates executables that are flagged by AntiViruses. Those are false positives. cx_Freeze is an alternative that allows to avoid such false positives.

#### PyInstaller 👎
``` bash
$ pip install pyinstaller
$ pyinstaller lunii-qt.spec
...
$ dist\lunii-qt
```

#### cx_Freeze 👍
```bash
$ pip install cx_Freeze
$ python setup.py build_exe
...
$ build/exe.win-amd64/lunii-qt
```

## Tricks

### macOS - Application Authorization
1. Double-click the file called `lunii-qt`.
2. You should see an error message "`lunii-qt` can’t be opened because it is from an unidentified developer".  
![](./res/macos_install_1.png)  
  Click "**OK**"
3. Go to System **Preferences** > **Security** and **Privacy** and click on the General tab.  
![](./res/macos_install_2.png)
4. At the bottom of the window you will see a message saying that `lunii-qt` was blocked. Click "**Open Anyway**".   
   If you do not see this message in the General tab, double-click `lunii-qt` again.  
   **NOTE :** You may have to click the "**unlock**" button and enter your password to be able to click "**Open Anyway**".
8. If you see another popup that says “`lunii-qt` is from an unidentified developer. Are you sure you want to open it?”, click "**Open**". If you don’t get this popup, just go to the same file and double-click it again.    
![](./res/macos_install_3.png)
9. Finally, you'll be informed that `lunii-qt` was downloaded from internet     
![](./res/macos_install_4.png)  
Click "**Open**", and you'll never get these messages in the future. 

### Third Party story metadata
You might have already loaded non-official stories to your device thanks to another app. When opening Lunii.QT, this 
story will appear as `Unknown story (maybe a User created story)...`.   
You can easily fix that by :  
1. Importing STUdio DB with menu `File/Import STUdio DB`
2. Dropping the corresponding archive as you'll do for loading.  
Lunii.QT will **only read the metadata** and add them locally, **skipping the rest** of the archive.


### Cache management
This application will download once for all the official story database and any request pictures to the application dedicated folder
* `$HOME/.lunii-qt/official.db`
* `$HOME/.lunii-qt/cache/*`

In case of any trouble, just remove this file and directory to force refresh

### Linux missing dependencies
If you encounter the following error when launching Lunii.QT on Linux:

```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

Available platform plugins are: offscreen, vkkhrdisplay, xcb, minimalegl, vnc, eglfs, minimal, linuxfb, wayland-egl, wayland.
```

This means that a required system library for the Qt graphical interface is missing.

**Solution:**  
Install the missing dependency by running the following command in your terminal:

```bash
sudo apt install libxcb-cursor0
```

After installing, try launching Lunii.QT again.  
If you still experience issues, make sure all other Qt dependencies are installed.

### v3 export
In order to suport story export from Lunii v3 hardware, you must place your device keys in here :
```bash
%HOME%\.lunii-qt\230230300XXXXX.keys
$HOME/.lunii-qt/230230300XXXXX.keys
```
It is a binary file with 0x10 bytes for Key and 0x10 bytes for IV
### ICO creation
```bash
magick convert logo.png -define icon:auto-resize="256,128,96,64,48,32,16"  logo.ico
```

## Credits
Thanks to :
* **olup** for STUdio archive format 
* **sniperflo** for v1 support, MacOs support & debug 
* **McFlyPartages** for Linux debug and other contributions 

# Links / Similar repos
* [Lunii v3 - Reverse Engineering](https://github.com/o-daneel/Lunii_v3.RE)
* [Lunii CLI tool](https://github.com/o-daneel/Lunii.PACKS)
* [STUdio - Story Teller Unleashed](https://marian-m12l.github.io/studio-website/)
* [(GitHub) STUdio, Story Teller Unleashed](https://github.com/marian-m12l/studio)
* [Lunii Admin](https://github.com/olup/lunii-admin) (a GO implementation of a STUdio alternative)
* [Lunii Admin Web](https://github.com/olup/lunii-admin-web) (same as previous but from a browser)  
* Icon trick for workflow using **[rcedit](https://github.com/electron/rcedit)**

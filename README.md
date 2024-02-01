:fr: [README en français](README_FR.md) :fr:

# Lunii.QT
A Python QT app to manage <u>Lunii</u> and <u>Flam</u> Storytellers, including **reorder** / **import** / **export** / **firmware download**   
for Windows / Linux / MacOs 11  
(compatible with STUdio archive, **with** transcoding)


### Hardware supported:
* **v1, v2**  (full Support)
* **v3**  (export requires device key file)  
* **Flam** (partial support, only reorder and firmware backup)

### Limitations
* Application <u>no longer</u> allows Official stories to be exported
* Audio transcoding requires FFMPEG v6 to be present ([more details](#audio-transcoding))

### Table of contents
<!-- TOC -->
* [Lunii.QT](#luniiqt)
  * [User Interface](#user-interface)
  * [Shortcuts](#shortcuts)
  * [Audio Transcoding](#audio-transcoding)
  * [Firmware upgrade](#firmware-upgrade)
    * [HowTo - Lunii](#howto---lunii)
    * [HowTo - Flam](#howto---flam)
  * [Supported archive formats (Lunii)](#supported-archive-formats-lunii)
  * [Python ? HowTo](#python--howto)
  * [Tricks](#tricks)
  * [Credits](#credits)
* [Links / Similar repos](#links--similar-repos)
<!-- TOC -->


## User Interface

<img src="./res/screenshot_about.png" width="450">  

 .  
<img src="./res/screenshot_main.png" width="600">  
<img src="./res/screenshot_debug.png" width="600">  


### Description

<img src="./res/screenshot_interface.png" width="600">  

1. The **menu bar**. It will notify you when an update is available  
   (just get it with Menu About/Update to v2.X.X)
2. The **location of your Lunii/Flam** when it's connected.   
   The button on the left updates automatic detection.
3. **Official DB refresh** : Updates the list of stories and related information from the official Lunii Store. Use it when some official are not recognized.
4. The **list of your stories** with UUID and Database (DB) origin.  
   The UUID: This unique identifier allows you to associate stories with their folder on the Lunii, thanks to the last eight characters that make up the name of the folder associated with that story.

   * **DB** stands for **Database**. This application supports two different databases
     - **O** - Lunii **O**fficial Database  
        _(all metadata are fed from Lunii servers)_
     - **T** - **T**hirdparty Database, also known as Unofficial or Custom Stories  
        _(Those metadata can't be fetched. They are completed upon story import)_


5. The **status bar**, you'll find 
   * your SNU (serial number)
   * the firmware version of your Lunii/Flam
   * the available space  
   * the number of stories it contains

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
| `Delete`       | Remove the selected item(s)      |
|                |                                  |
| `Ctrl+O`       | Open a Lunii/Flam device         |
| `Ctrl+L`       | Open debug log window            |
| `F1`           | About the app                    |
| `F5`           | Refresh devices                  |

## Audio Transcoding
Some third-party stories are using non MP3 files. Thus they can't be installed as it is on Lunii. It requires a **transcoding** step. This extra process is done using **FFMPEG** tool available here :  
https://github.com/eugeneware/ffmpeg-static/releases/latest  

**WARNING** : transcoding is <u>very long</u>, you should be patient. That's why you should prefer the [.plain.pk](#plainpk) format that use compatible audio.

### Installation
You must ensure that `ffmpeg` command is in your path.  
If you're lost, just can grab a standalone binary on the previous link, for you platform (Win/Linux/MacOs), and copy it beside this app, like this :
```
- 
 |- lunii-qt.exe
 |- ffmpeg.exe
```

1) Grab your ffmpeg release
2) Rename it to `ffmpeg.exe` or `ffmpeg` (depending on your host OS)
3) Copy beside lunii-qt.exe 

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
2. Menu **Tools/Get FW** Update
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
6. Copy it to the root dir of your device   
```
- 
 |- etc/
 |- str/
 |- .mdf
 |- update-main.enc
 |- update-comm.enc
 |- ... (other files)
```
7. Power OFF, Power ON, Wait : **TADA**  
   (if you reconnect your lunii on your pc, the `*.enc` should have been removed)

## Supported archive formats (Lunii)
**NOTE :** Flam stories are not yet supported
### .plain.pk
**Filename** :  `story_name.8B_UUID.plain.pk`  
**Ciphering** : None / Plain  
**Structure** :  

      uuid.bin
      ni
      li.plain
      ri.plain
      si.plain
      rf/000/XXYYXXYY.bmp
      sf/000/XXYYXXYY.mp3
### .v1.pk / .v2.pk
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
### ZIP (old Lunii.QT)
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

### ZIP (alternate)
**Filename** :  `AGE+] story_title DASHED_UUID.zip`  
**Ciphering** : Generic Key  
**Structure** : (same as [.v1.pk / .v2.pk](#v1pk--v2pk))

      00000000-0000-0000-0000-000000000000/ni
      00000000-0000-0000-0000-000000000000/li
      00000000-0000-0000-0000-000000000000/ri
      00000000-0000-0000-0000-000000000000/si
      00000000-0000-0000-0000-000000000000/rf/000/XXYYXXYY
      00000000-0000-0000-0000-000000000000/sf/000/XXYYXXYY

### 7z
**Filename** : `AGE+] story_title DASHED_UUID.7z`  
**Ciphering** : Generic Key  
**Structure** :  

      00000000-0000-0000-0000-000000000000/ni
      00000000-0000-0000-0000-000000000000/li
      00000000-0000-0000-0000-000000000000/ri
      00000000-0000-0000-0000-000000000000/si
      00000000-0000-0000-0000-000000000000/rf/000/XXYYXXYY
      00000000-0000-0000-0000-000000000000/sf/000/XXYYXXYY

### STUdio (ZIP / 7z)
**Filename** : `AGE+] story_title DASHED_UUID.zip .7z`  
**Ciphering** : None  

**Structure** :  

        assets/
        stroy.json
        thumbnail.png

## TODO
* config file to backup menu config (sizes / details)
* add picture to tree list ?


## Python ? HowTo

### Prepare env

Prepare a Virtual environment for your project and install requirements
```
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
```
$ pyside6-uic pkg/ui/main.ui -o pkg/ui/main_ui.py
$ pyside6-rcc resources.qrc -o resources_rc.py
```
### Run
```
$ python lunii-qt.py
```

### Build GUI executable
```
$ pip install pyinstaller
$ pyinstaller lunii-qt.spec
...
$ dist\lunii-qt
```

## Tricks

### Third Party story metadata
You might have already loaded non-official stories to your device thanks to another app. When opening Lunii.QT, this 
story will appear as `Unknown story (maybe a User created story)...`.   
You can easily fix that by dropping the corresponding archive as you'll do for loading.  
Lunii.QT will **only read the metadata** and add them locally, **skipping the rest** of the archive.


### Cache management
This application will download once for all the official story database and any request pictures to the application dedicated folder
* `$HOME/.lunii-qt/official.db`
* `$HOME/.lunii-qt/cache/*`

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
* **sniperflo** for v1 support, MacOs support & debug 
* **McFlyPartages** for Linux debug and other contributions 

# Links / Similar repos
* [Lunii v3 - Reverse Engineering](https://github.com/o-daneel/Lunii_v3.RE)
* [STUdio - Story Teller Unleashed](https://marian-m12l.github.io/studio-website/)
* [(GitHub) STUdio, Story Teller Unleashed](https://github.com/marian-m12l/studio)
* [Lunii Admin](https://github.com/olup/lunii-admin) (a GO implementation of a STUdio alternative)
* [Lunii Admin Web](https://github.com/olup/lunii-admin) (same as previous but from a browser)  
  

* Icon trick for workflow using **[rcedit](https://github.com/electron/rcedit)**
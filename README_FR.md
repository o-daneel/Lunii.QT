:uk: [Readme in English](./README.md) :uk:

# Lunii.QT
#### (peut être version obsolète)

Une application Python QT pour gérer sa fabrique à histoires (fah) <u>Lunii</u> et <u>Flam</u>, avec les opérations de  **organisation** / **importation** / **exportation** / **téléchargement du firmware**   
pour Windows / Linux / MacOs 11  
(compatible avec les archives STUdio, **avec** support de la conversion audio)

### Matériels pris en charge :
* Fah **v1** et **v2** (support complet)
* Fah **v3** (l'export requiert les clés  de la Fah)
* Flam (support partiel, tri des histoires et sauvegarde du firmware)

### Limitations :
* L'application <u>n'autorise plus</u> d'exporter les histoires officielles.
* Le transcodage audio nécessite la présence de [FFMPEG v6](#vérification)


### Table des matières
<!-- TOC -->
* [Lunii.QT](#luniiqt)
  * [Interface Utilisateur](#interface-utilisateur)
  * [Raccourcis clavier](#raccourcis-clavier)
  * [Fonctionnalités](#fonctionnalités)
  * [Transcodage audio](#transcodage-audio)
    * [Installation](#installation)
    * [Vérification](#vérification)
  * [Mise à jour du firmware](#mise-à-jour-du-firmware)
    * [Guide Pratique - Lunii](#guide-pratique---lunii)
    * [Guide Pratique - Flam](#guide-pratique---flam)
  * [Formats d'archives pris en charge (Lunii)](#formats-darchives-pris-en-charge-lunii)
  * [Python ? Guide Pratique](#python--guide-pratique)
  * [Astuces](#astuces)
    * [macOS - Authorisation de l'application](#macos---authorisation-de-lapplication)
    * [Métadonnées des histoires non-officielles](#métadonnées-des-histoires-non-officielles)
    * [Gestion du cache](#gestion-du-cache)
  * [Remerciements](#remerciements)
* [Liens / Dépôts similaires](#liens--dépôts-similaires)
<!-- TOC -->

## Interface Utilisateur

<img src="./res/screenshot_about.png" width="450">  
<img src="./res/screenshot_main.png" width="600">  
<img src="./res/screenshot_debug.png" width="600"> 

### Description

<img src="./res/screenshot_interface.png" width="600">  

1. La **barre de menu**. Elle vous informera lorsqu'une mise à jour de l'application est disponible  
   (il suffit d'aller dans Menu About/Update to v2.X.X)
2. **L'emplacement de votre Lunii/Flam** lorsqu'elle est connectée.   
   Le bouton à gauche relance la détection automatique.
3. Actualisation de la **base de données Officielle** : Met à jour la liste des histoires et leurs descriptions depuis le Luniistore. Utilisez ce bouton lorsque certaines histoires officielles ne sont pas reconnues.
4. La **liste de vos histoires** avec l'UUID et le type d'histoire (DB).  
   L'UUID : Un identifiant unique permettant de lier les histoires à leur dossier sur la Lunii/Flam. Les huit derniers caractères de l'UUID composent le nom du dossier de l'histoire.

   **DB** signifie **Base de données**. Cette application prend en charge deux bases de données différentes
     - **O** - Base de données **O**fficielle de Lunii  
        (Toutes les métadonnées proviennent des serveurs de Lunii).
     - **T** - base de données **T**ierce, également connue sous Non officielles ou Custom  
        (Ces métadonnées ne peuvent pas être récupérées, elles sont complétées lors de l'importation de l'histoire)
5. Dans la **barre d'état**, vous trouverez  
   * Votre SNU (numéro de série),
   * La version du firmware de votre Lunii/Flam
   * L'espace disponible sur la SD
   * Le nombre d'histoires

6. **Histoire cachées** (les entrées grisées dans la liste) sont toujours physiquement présente dans l'appareil, mais ne seront pas visible par l'application Luniistore. De la sorte, les histoires non officielles ne seront pas supprimées lors de la synchronisation. N'oubliez pas de bien "cacher" vos histoires avant de cliquer sur "synchroniser" !


## Raccourcis clavier

| Keys           | Actions                                             |
|----------------|-----------------------------------------------------|
| `Ctrl+Up`      | Déplace la ou les sélection(s) en première position |
| `Alt+Up`       | Déplace la ou les sélection(s) vers le haut         |
| `Alt+Down`     | Déplace la ou les sélection(s) vers le bas          |
| `Ctrl+Down`    | Déplace la ou les sélection(s) en dernière position |
|                |                                                     |
| `Ctrl+I`       | Importe une nouvelle histoire                       |
| `Ctrl+S`       | Exporte la sélection                                |
| `Ctrl+Shift+S` | Exporte toutes les histoires                        |
| `Ctrl+H`       | Masquer/Démasquer la sélection                      |
| `Delete`       | Supprime les histoires sélectionnées                |
|                |                                                     |
| `Ctrl+O`       | Ouvre le dossier d'une Lunii/Flamm                  |
| `Ctrl+L`       | Ouvre la fenêtre de debug                           |
| `F1`           | À propos de l'application                           |
| `F5`           | Réactualise les appareils                           |

## Fonctionnalités
* Détection automatique des **Mise à jour**
* **Import** / **Export** / **Suppression** des histoires
* Support des archives au format **STUdio**
* **Réorganisez** vos histoires dans votre ordre préféré
* **Cachez** les histoires  
  Dans le but de ne pas subir une suppression forcée des histoires non officielles durant la synchronisation avec l'application Luniistore, vous pouvez désormais "cacher" temporairement certaines histoires  
  (tous les fichiers sont conservés sur l'appareil)
* **Histoires perdues**  
  Trois nouveaux outils sont proposés pour gérer vos histoires perdues.   
  (souvent suite à un crash d'une autre application 😜)   
 ![](./res/screenshot_lost.png)
  Vous pouvez :
  * les lister  
    _(l'application tentera de réparer les histoires, en particulier les fichiers sur les Lunii v1/v2)_
  * les récupérer (si elles sont saines)
  * les supprimer (**attention, les fichiers seront supprimés**)  
* **Récupération du Firmware** pour votre appareil (cf. [cette section](#mise-à-jour-du-firmware))
  
## Transcodage audio
Certaines histoires tierces utilisent des fichiers non MP3. Ils ne peuvent donc pas être installés tels quels sur Lunii. Cela nécessite une étape de **transcodage**. Ce processus supplémentaire est réalisé à l'aide de l'outil **FFMPEG** disponible [ici](https://github.com/eugeneware/ffmpeg-static/releases/latest )  
 

**ATTENTION** : le transcodage est <u>très long</u>, il faut être patient. C'est pourquoi vous devriez préférer le format [.plain.pk](#plainpk) qui utilise un format audio compatible.

### Installation
Vous devez vous assurer que la commande `ffmpeg` se trouve dans votre PATH.  
Si vous êtes perdu, vous pouvez récupérer un binaire autonome sur le lien précédent, pour votre plateforme (Win/Linux/MacOs), et le copier à côté de cette application, comme ceci :

```
- 
 |- lunii-qt.exe
 |- ffmpeg.exe
```

1) Récupérez votre version de ffmpeg
2) Renommez-la en `ffmpeg.exe` ou `ffmpeg` (en fonction de votre système d'exploitation)
3) Copiez à côté de `lunii-qt.exe` ou `lunii-qt` (en fonction de votre système d'exploitation)

### Vérification 
Dans l'application, le menu `Tools` affiche l'état de la détection.
#### Non trouvé
![FFMPEG Non disponible](res/ffmpeg_off.png)  
#### Trouvé
![FFMPEG disponible](./res/ffmpeg_on.png)

## Mise à jour du firmware

Lunii.QT vous offre la possibilité de sauvegarder et de mettre à jour votre Firmware sans vous connecter au LuniiStore (vous ne perdrez pas vos histoires chargées non officielles). Cette procédure est **expérimentale** mais jusqu'à présent personne n'a rencontré de problèmes.

**NOTE 1:** Pensez à garder une sauvegarde de votre firmware pour Lunii v3 et FLAMs, dans le cas d'une mise à jour qui casserait l'astuce des histoires tierces. <u>Vous serez en mesure de rétrograder.</u>  
**NOTE 2:** Vous ne pouvez pas choisir la version du firmware. Vous n'obtiendrez que la **dernière version disponible** sur les serveurs de Lunii.


### Guide Pratique - Lunii
1. Sélectionnez une Lunii
2. Menu **Tools/Get FW Update**
3. Vous serez invité à vous connecter  
<img src="./res/screenshot_login.png" width="170">

4. Entrez vos identifiants Luniistore (ils ne sont pas sauvegardés pour des raisons de sécurité).  
   Vous pouvez vérifier ce point ici  
   https://github.com/o-daneel/Lunii.QT/blob/a8bd30e1864552687f235004085a417d7c6b00e6/pkg/main_window.py#L468-L475
5. Choisissez un emplacement où sauvegarder votre firmware (deux fichiers pour une Lunii v1)
6. Copiez-la dans le répertoire racine de votre lunii
7. Renommez-le en `fa.bin` (et aussi `fu.bin`  pour les Lunii v1)   
```
- 
 |- .contents
 |- .md
 |- .pi
 |- fa.bin
 |- ... (other files)
```
8. Éteindre, rallumer, attendre : **TADA**  
   (si vous reconnectez votre lunii sur votre pc, le `fa.bin` devrait avoir été supprimé)
   

### Guide Pratique - Flam
1. Sélectionnez une Lunii
2. Menu **Tools/Get FW Update**
3. Vous serez invité à vous connecter  
<img src="./res/screenshot_login.png" width="170">

4. Entrez vos identifiants Luniistore (ils ne sont pas sauvegardés pour des raisons de sécurité).  
   Vous pouvez vérifier ce point ici  
   https://github.com/o-daneel/Lunii.QT/blob/a8bd30e1864552687f235004085a417d7c6b00e6/pkg/main_window.py#L468-L475
5. Choisissez un emplacement où sauvegarder vos firmwares (`update-main.enc` and `update-comm.enc`)
6. Copiez-les dans le répertoire racine de votre Flam    
```
- 
 |- etc/
 |- str/
 |- .mdf
 |- update-main.enc
 |- update-comm.enc
 |- ... (other files)
```
7. Éteindre, rallumer, attendre : **TADA**  
   (si vous reconnectez votre lunii sur votre pc, les `*.enc` devraient avoir été supprimés)
      
   
## Formats d'archives pris en charge (Lunii)
**NOTE :** Les histoires Flam ne sont pas encore supportées
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
* Fichier de configuration pour sauvegarder la configuration du menu (tailles / détails)
* Ajout d'une image à la liste des arbres ?

## Python ? Guide Pratique

### Préparation de l'environnement

Commencer par cloner le dépot.  
Préparer l'environnement virtuel pour le projet et installer les dépendances.
```bash
$ python3 -m venv venv
```

Passez à votre venv
* sous Linux   
   `source venv/bin/activate`
* sous Windows   
  `.\venv\Scripts\activate.bat`

Installer les dépendances
```
$ pip install -r requirements.txt
```

**Linux** a besoin d'une dépendance supplémentaire.

```bash
$ apt install libxcb-cursor0
```
### Génération des UI
```bash
$ pyside6-uic pkg/ui/main.ui -o pkg/ui/main_ui.py
$ pyside6-rcc resources.qrc -o resources_rc.py
```
### Exécution
```bash
$ python lunii-qt.py
```

### Générer un exécutable GUI
**NOTE :** PyInstaller by its design generates executables that are flagged by AntiViruses. Those are false positives. cx_Freeze is an alternative that allows to avoid such false positives.

#### PyInstaller 👎
```bash
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

## Astuces

### macOS - Authorisation de l'application
1. Double cliquez sur le fichier `lunii-qt`.
2. Vous devez voir apparaître le message d'erreur suivant :     
![](./res/macos_install_1.png)  
  Cliquez sur "**OK**"
3. Allez dans **Préférences du système** > **Sécurité et confidentialité** et cliquez sur l'onglet **Général**.  
![](./res/macos_install_2.png)
4. En bas de la fenêtre, vous trouverez un message indiquant que  `lunii-qt` est bloqué. Cliquez sur "**Ouvrir quand même**".   
   Si vous ne voyez pas ce message sur l'onglet Général, double cliquez de nouveau sur `lunii-qt`.  
   **NOTE :** Il est possible que vous deviez en premier cliquer sur le bouton "**unlock**" puis entrer votre nom d'utilisateur / mot de passe pour pouvoir cliquer sur "**Ouvrir quand même**".
5. Une nouvelle popup apparait       
![](./res/macos_install_3.png)  
Cliquez sur "**Ouvrir**".   
Si vous n'avez pas eu cette popup, retournez juste double cliquer sur le fichier.
1. Pour finir, un dernier message vous informera de la sorte       
![](./res/macos_install_4.png)  
Cliquez sur "**Ouvrir**", et vous n'aurez plus ces avertissement à l'avenir. 

### Métadonnées des histoires non-officielles
Lors de l'utilisation de cette application, vous allez peut-être constater des hisoires marquées `Unknown story (maybe a User created story)...`. Il s'agit certainement d'une histoire tierce qui a été chargé par une autre application. Lunii.QT n'a donc pas connaissance des métadonnées associées (Titre, Description, Image).  
Il est possible de pallier à ce problème en glissant déposant l'archive de l'histoire dans l'application, comme pour la charger. Cette dernière étant déjà présente, Lunii.Qt ne va faire qu'**analyser les métadonnées** et les ajouter dans la base interne, en prenant soin de **ne pas recharger** l'histoire.

### Gestion du cache
Cette application téléchargera une fois pour toutes la base de données des histoires officielles et toutes les images demandées dans le dossier dédié à l'application.
* `$HOME/.lunii-qt/official.db`
* `$HOME/.lunii-qt/cache/*`

En cas de problème, il suffit de supprimer ce fichier et ce répertoire pour forcer le rafraîchissement.

### Exportation V3
Afin de supporter l'exportation d'histoires depuis une Lunii v3, vous devez placer vos clés de périphérique ici :
```bash
%HOME%\.lunii-qt\v3.keys
$HOME/.lunii-qt/v3.keys
```
Il s'agit d'un fichier binaire avec 0x10 octets pour la clé et 0x10 octets pour l'IV.

### Création de l'ICO
```bash
magick convert logo.png -define icon:auto-resize="256,128,96,64,48,32,16"  logo.ico
```

## Remerciements
Merci à :
* **olup** pour l'aide sur le format des archives STUdio  
* **sniperflo** pour le support de la v1 & debug 
* **McFlyPartages** pour le debug sous Linux et ses contributions 
*  ceux que j'oublie.... 👍

# Liens / Dépôts similaires
* [Lunii v3 - Reverse Engineering](https://github.com/o-daneel/Lunii_v3.RE)
* [Lunii CLI tool](https://github.com/o-daneel/Lunii.PACKS)
* [STUdio - Story Teller Unleashed](https://marian-m12l.github.io/studio-website/)
* [(GitHub) STUdio, Story Teller Unleashed](https://github.com/marian-m12l/studio)
* [Lunii Admin](https://github.com/olup/lunii-admin) (Une alternative en Go de STUdio)
* [Lunii Admin Web](https://github.com/olup/lunii-admin) (même chose que précédemment mais à partir d'un navigateur)
* Astuce de l'icone dans le workflow avec  **[rcedit](https://github.com/electron/rcedit)**
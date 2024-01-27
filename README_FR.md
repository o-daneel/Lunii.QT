:uk: [Readme in English](./README.md) :uk:

# Lunii.QT

Une application Python QT pour gérer Lunii Storyteller, y compris **la commande** / **l'importation** / **l'exportation** / **le téléchargement du firmware**   
pour Windows / Linux / MacOs 11  
(compatible avec l'archive STUdio, **avec** transcodage)

### Matériels pris en charge :
* Ma fabrique à histoire **V1** et **V2** (support complet)
* Ma fabrique à histoire **V3** (l'exportation nécessite un fichier clé de l'appareil)

### Limitations :
* L'application *ne permet plus* d'exporter les histoires officielles.
* Le transcodage audio nécessite la présence de [FFMPEG V6](#vérification)
* La **FLAM** n'est pas encore supportée (*travail en cours*)




### Table des matières
<!-- TOC -->
- [Lunii.QT](#luniiqt)
  - [Interface Utilisateur](#interface-utilisateur)
  - [Raccourcis clavier](#racourcis-clavier)
  - [Transcodage audio](#transcodage-audio)
  - [Mise à jour du Firmware](#mise-à-jour-du-firmware)
  - [Formats d'archives pris en charge](#formats-darchives-pris-en-charge)
  - [Construisez vos applications](#construisez-vos-applications)
  - [Astuces](#astuces)
  - [Crédits](#crédits)
- [Liens / Dépôts similaires](#liens--dépôts-similaires)
<!-- TOC -->

## Interface Utilisateur

<img src="./res/screenshot_about.png" width="450">  
<img src="./res/screenshot_main.png" width="600">  
<img src="./res/screenshot_debug.png" width="600"> 

### Description
![Interface de Lunii QT](./res/screenshot_interface.png")

1. La **barre de menu**. Elle vous informera lorsqu'une mise à jour est disponible  
   (il suffit de l'obtenir avec Menu About/Update to v2.X.X)
1. L'**emplacement de votre Lunii** lorsqu'elle est connectée.   
   Le bouton de gauche met à jour la détection automatique.
1. **Réactualisation de la base de données officielle** : Mettre à jour la liste des histoires et des informations connexes de la boutique officielle de Lunii. Utilisez-la lorsque certaines histoires officielles ne sont pas reconnues.
1. La **liste de vos histoires** avec l'UUID et l'origine de la base de données (DB).  
   L'UUID : Cet identifiant unique vous permet d'associer les histoires à leur dossier sur le Lunii, grâce aux huit derniers caractères qui composent le nom du dossier associé à cette histoire.

   **DB** signifie **Base de données**. Cette application prend en charge deux bases de données différentes
     - **O** - Base de données **officielle de Lunii  
        (Toutes les métadonnées proviennent des serveurs de Lunii).
     - **T** - base de données tierce, également connue sous le nom d'Histoires non officielles ou personnalisées  
        (Ces métadonnées ne peuvent pas être récupérées, elles sont complétées lors de l'importation de l'histoire)
1. Dans la **barre d'état**, vous trouverez : 
* Votre SNU (numéro de série),
* La version du firmware de votre Lunii,
* L'espace disponible  ,
* Le nombre d'histoires qu'il contient.

## Raccourcis clavier

| Keys           | Actions                                               |
|----------------|-------------------------------------------------------|
| `Ctrl+Up`      | Déplace la ou les sélection(s) en première position   |
| `Alt+Up`       | Déplace la ou les sélection(s) vers le haut           |
| `Alt+Down`     | Déplace la ou les sélection(s) vers le bas            |
| `Ctrl+Down`    | Déplace la ou les sélection(s) en dernière position   |
|                |                                                       |
| `Ctrl+I`       | Importe une nouvelle histoire                         |
| `Ctrl+S`       | Exporte la sélection                                  |
| `Ctrl+Shift+S` | Exporte toutes les histoires                          |
| `Delete`       | Supprime les histoires sélectionnées                  |
|                |                                                       |
| `Ctrl+O`       | Ouvre le dossier de votre Lunii                       |
| `Ctrl+L`       | Ouvre la fenêtre de debug                             |
| `F1`           | À propos de l'application                              |
| `F5`           | Réactualise les appareils                              |

## Transcodage audio
Certaines histoires tierces utilisent des fichiers non MP3. Ils ne peuvent donc pas être installés tels quels sur Lunii. Cela nécessite une étape de **transcodage**. Ce processus supplémentaire est réalisé à l'aide de l'outil **FFMPEG** disponible [ici](https://github.com/eugeneware/ffmpeg-static/releases/latest ) :     
 

**ATTENTION** : le transcodage est **très long**, il faut être patient. C'est pourquoi vous devriez préférer le format [.plain.pk](#plainpk) qui utilise un son compatible.

### Installation
Vous devez vous assurer que la commande `ffmpeg` se trouve dans votre chemin.  
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
Dans l'application, le menu `Outils` affiche l'état de la détection.
#### Non trouvé
![FFMPEG Non disponible](res/ffmpeg_off.png)  
#### Trouvé
![FFMPEG disponible](./res/ffmpeg_on.png)

## Mise à jour du firmware

Lunii.QT vous offre la possibilité de sauvegarder et de mettre à jour votre Firmware sans vous connecter au LuniiStore (vous ne perdrez pas vos histoires chargées non officielles). Cette procédure est **expérimentale** mais jusqu'à présent personne n'a rencontré de problèmes.

**NOTE 1:** Pensez à garder une sauvegarde de votre firmware pour Lunii v3 et FLAMs, dans le cas d'une mise à jour qui casserait l'astuce des histoires tierces. *Vous serez en mesure de rétrograder*.
**NOTE 2:** Vous ne pouvez pas choisir la version du firmware. Vous n'obtiendrez que la **dernière version disponible** sur les serveurs de Lunii.


### Guide Pratique
1. Sélectionnez un appareil Lunii
1. Menu Outils / Obtenir la mise à jour FW
1. Vous serez invité à vous connecter  
![Connexion](./res/screenshot_login.png)
1. Entrez vos identifiants Luniistore (ils ne sont pas sauvegardés pour des raisons de sécurité).  
   Vous pouvez vérifier ce point ici [main_window.py#L468](https://github.com/o-daneel/Lunii.QT/blob/a8bd30e1864552687f235004085a417d7c6b00e6/pkg/main_window.py#L468)
1. Choisissez un emplacement où sauvegarder la version de votre firmware
1. Copiez-la dans le répertoire racine de votre lunii
1. Renommez-le en `fa.bin`.   
```
- 
 |- .contents
 |- .md
 |- .pi
 |- fa.bin
 |- ... (other files)
```
1. Éteindre, rallumer, attendre : **TADA**  
   (si vous reconnectez votre lunii sur votre pc, le `fa.bin` devrait avoir été supprimé)
   
   
   
## Formats d'archives pris en charge
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

## À faire
* Ajouter le support de la FLAM ?
* Améliorer le traitement des archives 7z
* Fichier de configuration pour sauvegarder la configuration du menu (tailles / détails)
* Ajout d'une image à la liste des arbres ?

## Utilisation avec Python
### Préparation de l'environnement**

Commencer par cloner le dépot.
Préparer l'environnement virtuel pour le projet et installer les dépendances.
```bash
python -m venv venv
```

Passez à votre venv
* sous Linux   
   `source venv/bin/activate`
* sous Windows   
  `.\venv\Scripts\activate.bat`

Installer les dépendances
```
pip install -r requirements.txt
```

**Linux** a besoin d'une dépendance supplémentaire.

```bash
apt install libxcb-cursor0
```
### Construction du fichier UI**
```bash
$ pyside6-uic pkg/ui/main.ui -o pkg/ui/main_ui.py
$ pyside6-rcc resources.qrc -o resources_rc.py
```
### Démarrer**
```bash
python lunii-qt.py
```

### Construire l'exécutable GUI**
```bash
pip install pyinstaller
pyinstaller lunii-qt.spec
...
dist\lunii-qt
```

## Astuces

### Gestion du cache
Cette application téléchargera une fois pour toutes la base de données des histoires officielles et toutes les images demandées dans le dossier dédié à l'application.
* `$HOME/.lunii-qt/official.db`
* `$HOME/.lunii-qt/cache/*`

En cas de problème, il suffit de supprimer ce fichier et ce répertoire pour forcer le rafraîchissement.

### Exportation V3
Afin de supporter l'exportation d'histoires depuis le matériel Lunii v3, vous devez placer vos clés de périphérique ici :
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
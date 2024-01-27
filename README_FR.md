# Lunii.QT

Est une application, ecrite en Python QT, compatible Linux, Windows et MacOS 11, permettant la gestion de vos appareils Lunii Storyteller.

Elle permet de réorganiser, importer, exporter vos histoires, mais aussi de télécharger et installer le dernier firmware **#####Choix du firmware ous eulement le dernier ?#####**.

**Matériels pris en charge :**
* Ma fabrique à Histoire V1 et V2 (support complet),
* Ma fabrique à Histoire V3 (l'exportation necessiste un fichier clé de l'appareil)

**Limitations :**
* L'application ne permet plus d'exporter les histoires officielles.
* Le transcodage audio necessiste la presence de [FFMPEG V6](??????LIENS VERS LA SECTION????)
* La "FLAM" n'est pas ecore supportées (*travail en cours*)

**A faire**
* Ajouter le support de la FLAM ?
* Améliorer le traitement des archives 7z
* fFichier de configuration pour sauvegarder la configuration du menu (tailles / détails)
* Ajout d'une image à la liste des arbres ?


### Table des matieres
<!-- TOC -->

<!-- TOC -->

## Présentation de l'interface utilisateur
![Interface de Lunii QT](./res/lunii_qt_interface.png)

Voici l'interface de Luni QT.
1. La barre de menu.
1. L'emplacement de votre Lunii quand elle est connecté, le bouton a gauche permet d'actualiser la detection automatique.
1. Permet la mise à jour de la liste des histoires ainsi que les informations associé depuis le Lunii store officiel.
1. La liste de vos histoires avec le UUID et l'origine de la Base de donnée (DB). 
    1. L'UUID : Cet identifiant unique vous permet d'associer les histoire avec leur dossier sur la Lunii grace au 8 derniers caractere qui forme le nom du dossier associé a cette histoire.
    1. DB : Il ya deux base de données priset en charge. `O` pour la base de donnees officielle de Lunii (toutes les métadonnées proviennent des serveurs Lunii) et `T` pour la base de données tierce, egalement connu sous le nom d'Histoires non officielles ou personalisées (Ces métadonnées ne peuvent pas être récupérées, elles sont complétées lors de l'importation de l'histoire).
1. Dans cette barre d"tat vous retrouverez votre SNU (numero de série), la version du firmware de votre Lunii, l'espace disponnible et le nombre d'histoire qu'elle contient.

D'autres captures :
![Menu contextuel pour la gestion des histoires](./res/screenshot_main.png)
![Fenetre de débug](./res/screenshot_debug.png)
![Fenetre à propos](./res/screenshot_about.png)

### Racourcis clavier

| Keys           | Actions                                               |
|----------------|-------------------------------------------------------|
| `Ctrl+Up`      | Déplace la ou les selection(s) en premiere position   |
| `Alt+Up`       | Déplace la ou les selection(s) vers le haut           |
| `Alt+Down`     | Déplace la ou les selection(s) vers le bas            |
| `Ctrl+Down`    | Déplace la ou les selection(s) en derniere position   |
|                |                                                       |
| `Ctrl+I`       | Importe une nouvelle histoire                         |
| `Ctrl+S`       | Exporte la selection                                  |
| `Ctrl+Shift+S` | Exporte toutes les histoires                          |
| `Delete`       | Supprime les histoires sélectionnées                  |
|                |                                                       |
| `Ctrl+O`       | Ouvre le dossier de votre Lunii                       |
| `Ctrl+L`       | Ouvre la fenetre de debug                             |
| `F1`           | A-propo de l'application                              |
| `F5`           | Réactualis les appareils                              |


## Installation
### Sous Linux
Verifier la version de python installée sur votre machine avec la commande `python3 -V`.

```bash
anthony@McFly-Bureau:~$ python3 -V
Python 3.10.12
```

Si vous n'avez pas python d'installé lancer la commande suivante


```bash
sudo apt install python3
```

**Installer les dépendances**
```bash
sudo apt install libxcb-cursor0
```

Récuperer la [derniere version de Luni.QT pour Linux](https://github.com/o-daneel/Lunii.QT/releases) puis décompresser la.

Double cliquer sur `lunii-qt` pour lancer l'application.

#### Débug
En cas de probleme lors du lancement, essayer d'executer l'application depuis le Terminal dans le dossier avec la commande suivante. Il devrait vous afficher un message d'erreur qu'il faudra dans une issue.

```bash
./lunii-qt
```

### Sous Windows
>FAUX POSITIF : Votre système d'exploitation (et VirusTotal également) pourrait signaler l'executable comme une menace, mais ce n'est pas le cas. C'est un faux positif dû à pyinstaller. Les binaires sont générés par des workflows depuis GitHub, directement de Sources à Binaire.
>Ne faites jamais confiance à un exécutable sur internet, et [reconstruisez-le vous-même](#construiser-vos-applications) (vous arriverez au même résultat 😅).

Récuperer la [derniere version de Luni.QT pour Linux](https://github.com/o-daneel/Lunii.QT/releases) puis décompresser la.

Double cliquer sur `lunii-qt` pour lancer l'application.

## Transcodage audio
Certaines histoires tierces utilisent des fichiers non MP3. Ils ne peuvent donc pas être installés tels quels sur Lunii. Cela nécessite une étape de **transcodage**. Ce processus supplémentaire est réalisé à l'aide de l'outil **FFMPEG** disponible [ici](https://github.com/eugeneware/ffmpeg-static/releases/latest ) :     
 

**ATTENTION** : le transcodage est **très long**, il faut être patient. C'est pourquoi vous devriez préférer le format [.plain.pk](#plainpk) qui utilise un son compatible.

### Installation
Vous devez vous assurer que la commande `ffmpeg` se trouve dans votre chemin.  
Si vous êtes perdu, vous pouvez récupérer un binaire autonome sur le lien précédent, pour votre plateforme (Win/Linux/MacOs), et le copier à côté de cette application, comme ceci :

```tree
- 
 |- lunii-qt.exe
 |- ffmpeg.exe
```

1) Récupérez votre version de ffmpeg
2) Renommez-la en `ffmpeg.exe` ou `ffmpeg` (en fonction de votre système d'exploitation)
3) Copiez à côté de `lunii-qt.exe` ou `lunii-qt` (en fonction de votre système d'exploitation)

### Vérification 
Within the application, the Tools menu will display the status of detection.
#### Non trouvé
![FFMPEG Non disponible](res/ffmpeg_off.png)  
#### Trouvé
![FFMPEG disponible](./res/ffmpeg_on.png)

## Astuces
### Gestion du cache
Cette application téléchargera une fois pour toutes la base de données des histoires officielles et toutes les images demandées dans le dossier dédié à l'application
* `$HOME/.lunii-qt/official.db`
* `$HOME/.lunii-qt/cache/*`

En cas de problème, il suffit de supprimer ce fichier et ce répertoire pour forcer le rafraîchissement

### Exportation V3
IAfin de supporter l'exportation d'histoires depuis le matériel Lunii v3, vous devez placer vos clés de périphérique ici :
```bash
%HOME%\.lunii-qt\v3.keys
$HOME/.lunii-qt/v3.keys
```
Il s'agit d'un fichier binaire avec 0x10 octets pour la clé et 0x10 octets pour l'IV.

### Création de l'ICO
```bash
magick
```

## Construiser vos applications

**Preparationde l'environnement**

Commencer par cloner le dépot.
Préparer l'environement virtuele pour le projet et installer les dépendances.
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

**Linux** a besoin d'une dépendance supplmentaire.

```bash
apt install libxcb-cursor0
```
**Construction du fichier UI**
```bash
$ pyside6-uic pkg/ui/main.ui -o pkg/ui/main_ui.py
$ pyside6-rcc resources.qrc -o resources_rc.py
```
**Démarrer**
```bash
python lunii-qt.py
```

**Construire l'executable GUI**
```bash
pip install pyinstaller
pyinstaller lunii-qt.spec
...
dist\lunii-qt
```


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


## Credits
Merci à :
* **olup** pour les archives au format STUdio
* **sniperflo** pour le support et le debug de la V1

# Liens / Dépots similaires
* [Lunii v3 - Reverse Engineering](https://github.com/o-daneel/Lunii_v3.RE)
* [STUdio - Story Teller Unleashed](https://marian-m12l.github.io/studio-website/)
* [(GitHub) STUdio, Story Teller Unleashed](https://github.com/marian-m12l/studio)
* [Lunii Admin](https://github.com/olup/lunii-admin) (Une alternative enGo de STUdio)
* [Lunii Admin Web](https://github.com/olup/lunii-admin) (même chose que précédemment mais à partir d'un navigateur)

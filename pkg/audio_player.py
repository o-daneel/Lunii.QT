import os
import random
import zipfile

from PySide6.QtCore import QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
import py7zr

from pkg.api.constants import *
from pkg.api.story_parser import process_archive_type

os.environ["QT_LOGGING_RULES"] = "*.debug=false;*.info=false;*.warning=false;*.critical=true;*.ffmpeg.*=false"
os.environ["QT_FFMPEG_DEBUG"] = "0"

class AudioPlayer:
    def __init__(self):
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.current_playlist = None
        self.player.mediaStatusChanged.connect(self.handle_media_status)

        # Do zip extraction async in case of changin selected stories very quickly
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(300)
        self.filter_timer.timeout.connect(self._process_story_archive)
        
    def play_audio_from_list(self, urls):
        if self.current_playlist == urls:
            return

        self.stop(True)
        self.files = [QUrl(url) for url in urls]
        self.current_index = 0
        self.current_playlist = urls
        self.play_next()

    def play_story_from_device(self, device, folder):

        if self.current_playlist == folder:
            return

        self.files = []
        
        try:
            si_plain = device.get_plain_data(os.path.join(folder, "si")).decode("utf-8")
            si_plain = si_plain.rstrip('\x00')
            si_lines = [si_plain[i:i+12] for i in range(0, len(si_plain), 12)]
            for res in si_lines:
                self.files.append(QUrl.fromLocalFile(os.path.join(folder, "sf", res)))
        except:
            folder = os.path.join(folder, "sf", "000")
            self.files = []
            for filename in os.listdir(folder):
                self.files.append(QUrl.fromLocalFile(os.path.join(folder, filename)))
            
        self.current_index = 0
        self.current_playlist = folder
        self.play_next()

    def play_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
        elif len(self.files) > 0:
            self.current_index -= len(self.files) - 1
        else:
            return
            
        self.player.setSource(self.files[self.current_index])
        self.player.play()

    def play_next(self):
        if self.current_index < len(self.files):
            self.current_index += 1
        elif len(self.files) > 0:
            self.current_index = 0
        else:
            return

        self.player.setSource(self.files[self.current_index])
        self.player.play()
            
    def stop(self, clean_playlist = False):
        self.player.stop()

        if clean_playlist:
            self.player.setSource(QUrl(""))


    def pause(self):
        self.player.pause()
            
    def play(self):
        self.player.play()

    def handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next()

    def play_story_from_archive(self, story_path):
        
        if self.current_playlist == story_path:
            return
        
        self.current_playlist = story_path
        self.filter_timer.start()

    def _process_story_archive(self):
        self.stop()
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        if not os.path.exists(TEMP_DIR):
            os.mkdir(TEMP_DIR)

        self.files = []

        story_path = self.current_playlist
        archive_type = process_archive_type(story_path)
        if archive_type in [TYPE_LUNII_PLAIN, TYPE_LUNII_V2_ZIP, TYPE_LUNII_V3_ZIP, TYPE_STUDIO_ZIP]:
            self.extract_zip_audio_files(story_path)
        elif archive_type in [TYPE_LUNII_V2_7Z, TYPE_STUDIO_7Z]:
            self.extract_7z_audio_files(story_path)
        else:
            return
        
        random.shuffle(self.files)
        self.current_index = 0

        self.play_next()
    
    def extract_zip_audio_files(self, path):
        with zipfile.ZipFile(file=path) as zip_file:
            zip_contents = zip_file.namelist()

            for file in zip_contents:
                if "sf/000" in file or file.endswith(('.mp3', '.ogg')):
                    out_path = os.path.join(TEMP_DIR, file.split("/")[-1])
                    with zip_file.open(file) as src, open(out_path, "wb") as dst:
                        dst.write(src.read())
                    self.files.append(QUrl.fromLocalFile(out_path))

    def extract_7z_audio_files(self, path):
        with py7zr.SevenZipFile(file=path) as zip_file:
            contents = zip_file.readall().items()
            for fname, bio in contents:
                if "sf/000" in fname or fname.endswith(('.mp3', '.ogg')):
                    out_path = os.path.join(TEMP_DIR, fname.split("/")[-1])
                    with open(out_path, "wb") as dst:
                        dst.write(bio.read())
                    self.files.append(QUrl.fromLocalFile(out_path))

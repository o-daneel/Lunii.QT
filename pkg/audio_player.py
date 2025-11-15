import os
import random

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

class AudioPlayer:
    def __init__(self):
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.player.mediaStatusChanged.connect(self.handle_media_status)

    def play(self, folder):
        folder = os.path.join(folder, "sf", "000")
        self.files = []
        for filename in os.listdir(folder):
            self.files.append(QUrl.fromLocalFile(os.path.join(folder, filename)))
        
        random.shuffle(self.files)
        self.current_index = 0

        self.play_next()

    def play_next(self):
        if self.current_index < len(self.files):
            self.player.setSource(self.files[self.current_index])
            self.player.play()
            self.current_index += 1
            
    def stop(self):
        self.player.stop()

    def handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next()


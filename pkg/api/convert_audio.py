import os
import platform
import subprocess
import tempfile
from io import BytesIO

import ffmpeg
from mutagen.mp3 import MP3, BitrateMode, MONO

from pkg.api.constants import which_ffmpeg


def tags_removal_required(audio_data):
    audio_bytesio = BytesIO(audio_data)
    audio = MP3(audio_bytesio)
    return audio.tags


def transcoding_required(filename: str, audio_data):
    if not filename.lower().endswith(".mp3"):
        return True

    audio_bytesio = BytesIO(audio_data)
    audio = MP3(audio_bytesio)
    # print(f"MP3 {audio.info.bitrate // 1000}Kbps ({audio.info.bitrate_mode} / {audio.info.mode}) for {filename}")

    # not a 44,1 KHz
    if audio.info.sample_rate < 44100:
        return True

    # not the correct mode
    if not audio.info.bitrate_mode in [BitrateMode.UNKNOWN, BitrateMode.VBR, BitrateMode.CBR]:
        return True

    # not a mono audio
    if audio.info.mode != MONO:
        return True

    # to be kept as it is
    return False


def mp3_tag_cleanup(audio_data):
    audio_bytesio = BytesIO(audio_data)
    audio = MP3(audio_bytesio)

    # write the original MP3 data to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(audio_data)

        # remove tags and update file
        modified_audio = MP3(temp_file.name)
        modified_audio.delete()

        # read again the file without tags
        temp_file.seek(0)
        audio_data = temp_file.read()

    # cleaning up the mess
    os.remove(temp_file.name)

    # returning mp3 without tags
    return audio_data


def audio_to_mp3(audio_data):
    audio_mp3 = b""

    # Construct the ffmpeg command using the ffmpeg-python syntax
    ffmpeg_cmd = (
        ffmpeg.input('pipe:0')
        .output('pipe:', format='mp3',
                codec='libmp3lame',
                map='0:a',
                ar='44100',
                ac='1',
                aq='5',
                # ab='128k', # NOOOOOOOOOOO CBR 😡
                map_metadata='-1',
                write_xing='0',
                id3v2_version='0'
               )
        .global_args('-threads', '0')
        .compile(cmd=which_ffmpeg())
    )

    current_os = platform.system()
    if current_os == "Windows":
        flags = subprocess.CREATE_NO_WINDOW
    else:
        flags = 0

    # Run the ffmpeg command using subprocess with stdin and stdout pipes
    process = subprocess.Popen(ffmpeg_cmd,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               creationflags=flags)

    # Feed the audio data to the stdin of the subprocess
    stdout, stderr = process.communicate(input=audio_data)

    # Check for errors
    if process.returncode != 0:
        print(f"Error: {stderr.decode('utf-8')}")
    else:
        # 'stdout' now contains the MP3 audio data
        audio_mp3 = stdout

    # print(f"{len(audio_mp3)//1024}K")
    return audio_mp3
#
# INPUT = 'C:/Work/dev/lunii-sd/packs/transcode/2d1a50ec4800416d935d4ef04805a115cbe0e85f.ogg'
# OUTPUT = 'C:/Work/dev/lunii-sd/packs/transcode/2d1a50ec4800416d935d4ef04805a115cbe0e85f.mp3'
#
# with open(INPUT, 'rb') as fp:
#     audio_data = fp.read()
#     mp3 = audio_to_mp3(audio_data)
#
#     with open(OUTPUT, 'wb') as fw:
#         fw.write(mp3)

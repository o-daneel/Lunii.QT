import platform
import subprocess
import ffmpeg


def audio_to_mp3(audio_data):
    audio_mp3 = b""

    # Construct the ffmpeg command using the ffmpeg-python syntax
    ffmpeg_cmd = (
        ffmpeg.input('pipe:0')
        .output('pipe:', format='mp3', codec='libmp3lame',
                map='0:a',
                ar='44100',
                ac='1',
                # aq='9',
                ab='64k',
                map_metadata='-1',
                write_xing='0',
                id3v2_version='0'
               )
        .compile()
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
# INPUT = 'C:/Work/dev/lunii-packs/test/packs/transcode/2d1a50ec4800416d935d4ef04805a115cbe0e85f.ogg'
# OUTPUT = 'C:/Work/dev/lunii-packs/test/packs/transcode/2d1a50ec4800416d935d4ef04805a115cbe0e85f.mp3'
#
# with open(INPUT, 'rb') as fp:
#     audio_data = fp.read()
#     mp3 = audio_to_mp3(audio_data)
#
#     with open(OUTPUT, 'wb') as fw:
#         fw.write(mp3)

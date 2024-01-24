# import io
import ffmpeg

def audio_to_mp3(audio_data):
    audio_mp3, err = (
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
        .run(input=audio_data, capture_stdout=True, capture_stderr=True)
    )

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

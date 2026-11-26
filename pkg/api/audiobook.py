"""
Audiobook -> STUdio pack builder.

Turns a list of MP3 chapters + a cover image into a STUdio archive (story.json + assets/)
that Lunii.QT can import on a Lunii or a Flam (firmware v2.x).

Pack structure (what the child sees on the device):

    [Cover]  title announced          --OK-->  [Chapter menu]
    [Chapter menu]  wheel = pick a chapter, each one announced  --OK-->  [Chapter N playing]
    [Chapter N playing]  end of audio  -->  Chapter N+1 (autoplay)   (last one -> back to menu)
                         HOME          -->  Chapter menu, positioned on chapter N
"""
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, List, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PySide6.QtCore import QCoreApplication, QLocale

from pkg.api.constants import which_ffmpeg

SCREEN_SIZE = (320, 240)
AUDIO_EXT = (".mp3", ".m4a", ".m4b", ".aac", ".ogg", ".opus", ".wav", ".flac", ".wma")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif")
COVER_NAMES = ("cover", "folder", "front", "couverture", "albumart")

CTRL_COVER = {"wheel": True, "ok": True, "home": False, "pause": False, "autoplay": False}
CTRL_MENU = {"wheel": True, "ok": True, "home": True, "pause": False, "autoplay": False}
CTRL_PLAY = {"wheel": False, "ok": False, "home": True, "pause": True, "autoplay": True}


class BuildAborted(Exception):
    pass


@dataclass
class Chapter:
    path: str
    name: str


# ---------------------------------------------------------------------------
# helpers used by the UI
# ---------------------------------------------------------------------------
def natural_key(text: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def _strip_track_number(text: str) -> str:
    # "02 - Chapitre 1" -> "Chapitre 1", but keeps "1984" or "3 petits cochons"
    return re.sub(r"^\s*\d{2,}[\s._\-–)]+(?=\S)|^\s*\d+\s*[._\-–)]+\s*(?=\S)", "", text).replace("_", " ").strip()


def guess_chapter_name(path: str, index: int) -> str:
    """ID3/MP4 title tag if any, else a cleaned-up file name."""
    try:
        from mutagen import File as MutagenFile
        tags = MutagenFile(path, easy=True)
        if tags and tags.get("title"):
            title = _strip_track_number(str(tags.get("title")[0]))
            if title:
                return title
    except Exception:
        pass

    cleaned = _strip_track_number(Path(path).stem)
    return cleaned if cleaned else default_chapter_name(index)


def default_chapter_name(index: int) -> str:
    return QCoreApplication.translate("Audiobook", "Chapter {}").format(index)


def guess_book_title(paths: List[str]) -> str:
    if not paths:
        return ""
    try:
        from mutagen import File as MutagenFile
        tags = MutagenFile(paths[0], easy=True)
        if tags and tags.get("album"):
            return str(tags.get("album")[0]).strip()
    except Exception:
        pass
    return Path(paths[0]).parent.name


def find_cover(paths: List[str]) -> Optional[bytes]:
    """Looks for cover.jpg/folder.jpg next to the files, then for embedded artwork."""
    if not paths:
        return None
    folder = Path(paths[0]).parent
    candidates = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT)
    for p in candidates:
        if p.stem.lower() in COVER_NAMES:
            return p.read_bytes()
    if len(candidates) == 1:
        return candidates[0].read_bytes()

    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(paths[0])
        if audio is not None and audio.tags is not None:
            for key in audio.tags.keys():
                if key.startswith("APIC"):
                    return audio.tags[key].data
            if "covr" in audio.tags:
                return bytes(audio.tags["covr"][0])
        if hasattr(audio, "pictures") and audio.pictures:
            return audio.pictures[0].data
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# images
# ---------------------------------------------------------------------------
def _font(size: int, bold=True):
    names = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
    for name in names:
        for folder in ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", ""]:
            try:
                return ImageFont.truetype(os.path.join(folder, name) if folder else name, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _wrap(draw, text, font, max_width, max_lines):
    words, lines, line = text.split(), [], ""
    for word in words:
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textlength(lines[-1] + "…", font=font) > max_width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines


def _open_cover(cover: Optional[bytes]) -> Image.Image:
    if cover:
        try:
            return Image.open(BytesIO(cover)).convert("RGB")
        except Exception:
            pass
    return Image.new("RGB", SCREEN_SIZE, (40, 60, 110))


def _fit(img: Image.Image) -> Image.Image:
    """Cover fit on a blurred version of itself (no stretching)."""
    bg = img.copy()
    bg_ratio = max(SCREEN_SIZE[0] / bg.width, SCREEN_SIZE[1] / bg.height)
    bg = bg.resize((int(bg.width * bg_ratio) + 1, int(bg.height * bg_ratio) + 1))
    left, top = (bg.width - SCREEN_SIZE[0]) // 2, (bg.height - SCREEN_SIZE[1]) // 2
    bg = bg.crop((left, top, left + SCREEN_SIZE[0], top + SCREEN_SIZE[1])).filter(ImageFilter.GaussianBlur(12))

    fg = img.copy()
    fg.thumbnail(SCREEN_SIZE)
    bg.paste(fg, ((SCREEN_SIZE[0] - fg.width) // 2, (SCREEN_SIZE[1] - fg.height) // 2))
    return bg


def make_cover_image(cover: Optional[bytes], title: str) -> bytes:
    img = _fit(_open_cover(cover))
    if not cover:
        draw = ImageDraw.Draw(img)
        font = _font(30)
        lines = _wrap(draw, title, font, 290, 4)
        y = (SCREEN_SIZE[1] - len(lines) * 36) // 2
        for line in lines:
            draw.text((SCREEN_SIZE[0] // 2, y), line, font=font, fill="white", anchor="ma")
            y += 36
    out = BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


def make_chapter_image(cover: Optional[bytes], number: int, total: int, name: str) -> bytes:
    base = _fit(_open_cover(cover)).filter(ImageFilter.GaussianBlur(6))
    shade = Image.new("RGB", SCREEN_SIZE, (0, 0, 0))
    img = Image.blend(base, shade, 0.55)
    draw = ImageDraw.Draw(img)

    # chapter name, as big as it fits
    for size, max_lines in ((44, 2), (34, 3), (26, 4)):
        font = _font(size)
        lines = _wrap(draw, name, font, 300, max_lines)
        if not lines[-1].endswith("…"):
            break
    line_h = int(size * 1.2)
    y = (200 - len(lines) * line_h) // 2 + 4
    for line in lines:
        draw.text((SCREEN_SIZE[0] // 2, y), line, font=font, fill="white", anchor="ma")
        y += line_h

    # position in the book
    draw.text((SCREEN_SIZE[0] // 2, 206), f"{number} / {total}", font=_font(20, bold=False), fill=(220, 220, 220), anchor="ma")
    out = BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


def make_thumbnail(cover: Optional[bytes], title: str) -> bytes:
    if not cover:
        return make_cover_image(None, title)
    img = _open_cover(cover)
    img.thumbnail((512, 512))
    out = BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


# ---------------------------------------------------------------------------
# audio
# ---------------------------------------------------------------------------
def _run(cmd):
    flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-800:])


def to_lunii_mp3(ffmpeg: str, src: str, dst: str):
    """Same settings as Lunii.QT transcoding: mono, 44.1kHz, VBR, no tags."""
    _run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
          "-map", "0:a:0", "-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-q:a", "5",
          "-map_metadata", "-1", "-write_xing", "0", "-id3v2_version", "0", dst])


def tts_available() -> bool:
    return platform.system() == "Windows"


def synthesize(items: List[tuple], workdir: str, lang: str = ""):
    """Windows speech synthesis, with a voice matching `lang` (ex: 'fr') if installed. items = [(text, wav_path)]"""
    job = os.path.join(workdir, "tts.json")
    with open(job, "w", encoding="utf-8") as fp:
        json.dump([{"text": t, "path": p} for t, p in items], fp, ensure_ascii=False)
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$v = $s.GetInstalledVoices() | Where-Object {{ $_.Enabled -and $_.VoiceInfo.Culture.Name -like '{lang}*' }} | Select-Object -First 1;"
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) };"
        "$s.Rate = -1;"
        f"$jobs = Get-Content -Raw -Encoding UTF8 '{job}' | ConvertFrom-Json;"
        "foreach ($j in $jobs) { $s.SetOutputToWaveFile($j.path); $s.Speak($j.text) };"
        "$s.Dispose()"
    )
    _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])


def make_silence(ffmpeg: str, dst: str, seconds=0.5):
    _run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
          "-t", str(seconds), "-c:a", "libmp3lame", "-q:a", "5", "-write_xing", "0", "-id3v2_version", "0", dst])


# ---------------------------------------------------------------------------
# pack builder
# ---------------------------------------------------------------------------
def _asset_name(used: set, ext: str) -> str:
    # Lunii.QT keys assets on the last 8 chars of their name: keep them unique
    while True:
        name = uuid.uuid4().hex
        if name[-8:].upper() not in used:
            used.add(name[-8:].upper())
            return name + ext


def safe_filename(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .") or "livre_audio"


def build_audiobook_pack(title: str,
                         chapters: List[Chapter],
                         out_zip: str,
                         cover: Optional[bytes] = None,
                         description: str = "",
                         announce: bool = True,
                         night_mode: bool = False,
                         progress: Optional[Callable[[int, int, str], None]] = None,
                         abort: Optional[Callable[[], bool]] = None) -> str:
    """Builds the STUdio zip, returns its path. progress(step, total, message)."""
    if not chapters:
        raise ValueError(QCoreApplication.translate("Audiobook", "No chapter to convert"))
    ffmpeg = which_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(QCoreApplication.translate("Audiobook", "FFMPEG not found: it is required to convert the audio files."))

    def report(step, total, msg):
        if progress:
            progress(step, total, msg)
        if abort and abort():
            raise BuildAborted()

    total = len(chapters) + 3
    with tempfile.TemporaryDirectory(prefix="lunii_audiobook_") as tmp:
        used_img, used_snd = set(), set()
        assets = {}  # asset name -> local file

        def add_bytes(name, data):
            path = os.path.join(tmp, name)
            with open(path, "wb") as fp:
                fp.write(data)
            assets[name] = path
            return name

        # --- images
        report(0, total, QCoreApplication.translate("Audiobook", "Creating pictures..."))
        img_cover = add_bytes(_asset_name(used_img, ".png"), make_cover_image(cover, title))
        img_chapters = [add_bytes(_asset_name(used_img, ".png"), make_chapter_image(cover, i + 1, len(chapters), ch.name))
                        for i, ch in enumerate(chapters)]

        # --- announcements (title + each chapter name)
        report(1, total, QCoreApplication.translate("Audiobook", "Creating voice announcements..."))
        snd_title = _asset_name(used_snd, ".mp3")
        snd_menus = [_asset_name(used_snd, ".mp3") for _ in chapters]
        texts = [title] + [ch.name for ch in chapters]
        targets = [snd_title] + snd_menus
        spoken = False
        if announce and tts_available():
            try:
                wavs = [(t, os.path.join(tmp, f"tts_{i}.wav")) for i, t in enumerate(texts)]
                synthesize(wavs, tmp, QLocale.system().name()[:2])
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(lambda a: to_lunii_mp3(ffmpeg, a[0][1], os.path.join(tmp, a[1])), zip(wavs, targets)))
                spoken = True
            except Exception:
                spoken = False
        if not spoken:
            silence = os.path.join(tmp, targets[0])
            make_silence(ffmpeg, silence)
            for name in targets[1:]:
                shutil.copyfile(silence, os.path.join(tmp, name))
        for name in targets:
            assets[name] = os.path.join(tmp, name)

        # --- chapters audio
        snd_chapters = []
        done = 0
        report(2, total, QCoreApplication.translate("Audiobook", "Converting audio {}/{}...").format(0, len(chapters)))
        with ThreadPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 1))) as pool:
            futures = []
            for ch in chapters:
                name = _asset_name(used_snd, ".mp3")
                snd_chapters.append(name)
                assets[name] = os.path.join(tmp, name)
                futures.append(pool.submit(to_lunii_mp3, ffmpeg, ch.path, assets[name]))
            for fut, ch in zip(futures, chapters):
                try:
                    fut.result()
                except Exception as e:
                    for f in futures:
                        f.cancel()
                    raise RuntimeError(QCoreApplication.translate("Audiobook", "Unable to convert '{}':").format(Path(ch.path).name) + f"\n{e}")
                done += 1
                report(2 + done, total, QCoreApplication.translate("Audiobook", "Converting audio {}/{}...").format(done, len(chapters)))

        # --- story.json
        n = len(chapters)
        id_cover = str(uuid.uuid4())   # first stage node uuid == pack uuid
        id_menus = [str(uuid.uuid4()) for _ in chapters]
        id_plays = [str(uuid.uuid4()) for _ in chapters]
        act_menu, act_play = str(uuid.uuid4()), str(uuid.uuid4())

        stages = [{
            "uuid": id_cover, "type": "cover", "name": title, "squareOne": True,
            "image": img_cover, "audio": snd_title,
            "okTransition": {"actionNode": act_menu, "optionIndex": 0},
            "homeTransition": None, "controlSettings": CTRL_COVER,
        }]
        for i in range(n):
            stages.append({
                "uuid": id_menus[i], "type": "stage", "name": f"Menu - {chapters[i].name}",
                "image": img_chapters[i], "audio": snd_menus[i],
                "okTransition": {"actionNode": act_play, "optionIndex": i},
                "homeTransition": None, "controlSettings": CTRL_MENU,
            })
        for i in range(n):
            nxt = ({"actionNode": act_play, "optionIndex": i + 1} if i + 1 < n
                   else {"actionNode": act_menu, "optionIndex": 0})
            stages.append({
                "uuid": id_plays[i], "type": "stage", "name": chapters[i].name,
                "image": None, "audio": snd_chapters[i],
                "okTransition": nxt,
                "homeTransition": {"actionNode": act_menu, "optionIndex": i},
                "controlSettings": CTRL_PLAY,
            })

        story = {
            "format": "v1",
            "version": 1,
            "title": title,
            "description": description or (QCoreApplication.translate("Audiobook", "Audiobook - {} chapters").format(n) if n > 1
                                           else QCoreApplication.translate("Audiobook", "Audiobook - 1 chapter")),
            "nightModeAvailable": night_mode,
            "stageNodes": stages,
            "actionNodes": [
                {"id": act_menu, "name": "Chapter menu", "options": id_menus},
                {"id": act_play, "name": "Playback", "options": id_plays},
            ],
        }

        # --- zip
        report(total - 1, total, QCoreApplication.translate("Audiobook", "Writing archive..."))
        Path(out_zip).parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_STORED) as zf:
            zf.writestr("story.json", json.dumps(story, ensure_ascii=False, indent=1))
            zf.writestr("thumbnail.png", make_thumbnail(cover, title))
            for name, path in assets.items():
                zf.write(path, f"assets/{name}")
        report(total, total, QCoreApplication.translate("Audiobook", "Pack created"))

    return out_zip

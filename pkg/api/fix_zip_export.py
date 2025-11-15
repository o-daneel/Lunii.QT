import zipfile
import os

original_from_file = zipfile.ZipInfo.from_file

def safe_from_file(filename, arcname=None, *, strict_timestamps=True):
    try:
        return original_from_file(filename, arcname, strict_timestamps=strict_timestamps)
    except OSError as e:
        if e.errno == 22:  
            st = os.stat(filename)
            zinfo = zipfile.ZipInfo(arcname if arcname else filename)
            zinfo.date_time = (2020, 1, 1, 0, 0, 0)
            zinfo.file_size = st.st_size
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            return zinfo
        else:
            raise

zipfile.ZipInfo.from_file = safe_from_file
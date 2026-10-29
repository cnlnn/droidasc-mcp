from typing import BinaryIO

# [slim] Removed loguru (MyFilter/set_log) and the asn1crypto X509 certificate
# helpers (get_certificate_name_string/parse_public/calculate_fingerprint). None
# are on the decompile path; dex only pulls read_at from here. This keeps loguru
# and asn1crypto out of the import graph so nuitka won't bundle them. 20260801


def read_at(buff: BinaryIO, offset: int, size: int = -1) -> bytes:
    idx = buff.tell()
    buff.seek(offset)
    d = buff.read(size)
    buff.seek(idx)
    return d


def readFile(filename: str, binary: bool = True) -> bytes:
    """
    Open and read a file
    :param filename: filename to open and read
    :param binary: `True` if the file should be read as binary
    :return: bytes if binary is `True`, str otherwise
    """
    with open(filename, 'rb' if binary else 'r') as f:
        return f.read()

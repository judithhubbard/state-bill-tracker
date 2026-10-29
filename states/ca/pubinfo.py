"""Reads files out of the Legislature's pubinfo zips (downloads.leginfo.legislature.ca.gov) without downloading
the whole zip: most of each 1.2 GB zip is committee analyses and bill text, and the site needs only the tables
(about 11 MB zipped) and a few texts. The server accepts HTTP range requests, so this reads the zip's directory
from its end, then fetches the wanted files in a few ranges.

Requests go through curl: the server turns away Python's default client.
"""
import re, struct, subprocess, time, zlib

BASE = "https://downloads.leginfo.legislature.ca.gov"


def _curl(args):
    for attempt in range(4):
        r = subprocess.run(["curl", "-sSf", "--max-time", "300", *args], capture_output=True)
        if r.returncode == 0:
            return r.stdout
        time.sleep(5 * (attempt + 1))
    raise SystemExit(f"failed: curl {' '.join(args)}: {r.stderr.decode(errors='replace').strip()}")


def head(url):
    """(size, last-modified) of a file on the server, or None if it isn't there."""
    r = subprocess.run(["curl", "-sSI", "--max-time", "60", url], capture_output=True, text=True)
    if not re.search(r"^HTTP/\S+ 200", r.stdout, re.M):
        return None
    size = re.search(r"(?im)^content-length: (\d+)", r.stdout)
    mod = re.search(r"(?im)^last-modified: (.+?)\s*$", r.stdout)
    return int(size[1]) if size else 0, mod[1] if mod else ""


def _range(url, start, end):
    return _curl(["-r", f"{start}-{end}", url])


class Zip:
    """A remote zip's directory: name -> (offset of its local header, compressed size, method)."""

    def __init__(self, url):
        self.url = url
        self.size = head(url)[0]
        tail = _range(url, max(0, self.size - 65536 - 22), self.size - 1)
        i = tail.rfind(b"PK\x05\x06")
        if i < 0:
            raise SystemExit(f"{url}: no zip directory")
        count, dsize, doff = struct.unpack("<HII", tail[i + 10:i + 20])
        if doff == 0xFFFFFFFF or count == 0xFFFF:  # zip64: the real values are in the zip64 end record
            j = tail.rfind(b"PK\x06\x07", 0, i)
            z64 = struct.unpack("<Q", tail[j + 8:j + 16])[0]
            rec = _range(url, z64, z64 + 55)
            count, dsize, doff = struct.unpack("<QQQ", rec[32:56])
        d = _range(url, doff, doff + dsize - 1)
        self.files, p = {}, 0
        while p + 46 <= len(d) and d[p:p + 4] == b"PK\x01\x02":
            method, = struct.unpack("<H", d[p + 10:p + 12])
            csize, usize = struct.unpack("<II", d[p + 20:p + 28])
            nlen, xlen, clen = struct.unpack("<HHH", d[p + 28:p + 34])
            off, = struct.unpack("<I", d[p + 42:p + 46])
            name = d[p + 46:p + 46 + nlen].decode("utf-8", "replace")
            extra = d[p + 46 + nlen:p + 46 + nlen + xlen]
            # zip64 sizes and offsets, in the order of the fields that are 0xFFFFFFFF
            q = 0
            while q + 4 <= len(extra):
                tag, ln = struct.unpack("<HH", extra[q:q + 4])
                if tag == 1:
                    vals, k = list(struct.unpack(f"<{ln // 8}Q", extra[q + 4:q + 4 + ln // 8 * 8])), 0
                    if usize == 0xFFFFFFFF:
                        usize, k = vals[k], k + 1
                    if csize == 0xFFFFFFFF:
                        csize, k = vals[k], k + 1
                    if off == 0xFFFFFFFF:
                        off = vals[k]
                q += 4 + ln
            self.files[name] = (off, csize, method)
            p += 46 + nlen + xlen + clen

    def read(self, names, chunk=16 << 20, gap=256 << 10):
        """{name: bytes} for the named files, fetched in as few ranges as fit `chunk` bytes, joining neighbors
        only when less than `gap` bytes of other files lie between them."""
        want = sorted((self.files[n][0], n) for n in names if n in self.files)
        out, i = {}, 0
        while i < len(want):
            j, start = i, want[i][0]
            # A local header is 30 bytes plus the name and an extra field (read below); allow 1 KB.
            end = self.files[want[i][1]][0] + self.files[want[i][1]][1] + 1024
            while j + 1 < len(want) and want[j + 1][0] - end <= gap and \
                    self.files[want[j + 1][1]][0] + self.files[want[j + 1][1]][1] + 1024 - start <= chunk:
                j += 1
                end = self.files[want[j][1]][0] + self.files[want[j][1]][1] + 1024
            data = _range(self.url, start, min(end, self.size) - 1)
            for off, name in want[i:j + 1]:
                p = off - start
                nlen, xlen = struct.unpack("<HH", data[p + 26:p + 30])
                csize, method = self.files[name][1], self.files[name][2]
                body = data[p + 30 + nlen + xlen:p + 30 + nlen + xlen + csize]
                out[name] = zlib.decompress(body, -15) if method == 8 else body
            i = j + 1
        return out

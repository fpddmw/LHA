"""Bounded, exact decoded-pixel cache; it never drops frames or re-encodes evidence."""
from collections import OrderedDict
import threading
from evaluation.media import decode
from evaluation.protocol import file_hash


class DecodeCache:
    def __init__(self, max_bytes=512 * 1024 * 1024, decoder=decode):
        if type(max_bytes) is not int or max_bytes < 0:
            raise ValueError("Decode cache limit must be a nonnegative integer")
        self.max_bytes, self.decoder = max_bytes, decoder
        self.lock = threading.Lock()
        self.entries, self.bytes = OrderedDict(), 0

    def __call__(self, path):
        key = file_hash(path)
        with self.lock:
            if key in self.entries:
                value, size = self.entries.pop(key)
                self.entries[key] = (value, size)
                return value
            value = self.decoder(path)
            size = sum(f.width * f.height * 3 for f in value["frames"])
            while self.entries and self.bytes + size > self.max_bytes:
                _, (_, removed) = self.entries.popitem(last=False)
                self.bytes -= removed
            if size <= self.max_bytes:
                self.entries[key] = (value, size)
                self.bytes += size
            return value

import json, os
from typing import Dict

class IndexManifest:
    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, float] = {}
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def mtime(self, filepath: str) -> float:
        try:
            return os.path.getmtime(filepath)
        except Exception:
            return 0.0

    def diff(self, files):
        """Return (changed, unchanged) lists based on mtime diff."""
        changed, unchanged = [], []
        for f in files:
            m = self.mtime(f)
            if self.data.get(f) != m:
                changed.append(f)
            else:
                unchanged.append(f)
        return changed, unchanged

    def update(self, files):
        for f in files:
            self.data[f] = self.mtime(f)

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f)
        os.replace(tmp, self.path)

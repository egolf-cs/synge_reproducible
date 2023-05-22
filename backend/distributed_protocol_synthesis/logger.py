from pprint import pprint
from pathlib import Path
import time


class BasicLogger:

    def __init__(self, logger_id, emit_content=True) -> None:
        self.data_dir = f"{Path(__file__).parent}/logs/{logger_id}"
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        self.files = {}
        self.emit_content = emit_content

    def emit(self, id, fn, hdr, content):
        d = {
            "id" : id,
            "fn" : fn,
            "hdr" : hdr,
            "time" : time.time()
        }
        if self.emit_content:
            d["content"] = str(content)
        if id not in self.files:
            self.files[id] = open(f"{self.data_dir}/{id}.out", "w")
        print(d,file=self.files[id])

    def __del__(self):
        for _, file in self.files.items():
            file.close()

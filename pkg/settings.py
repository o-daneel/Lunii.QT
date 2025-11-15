import json
import threading

class Settings:
    def __init__(self, filename="settings.json"):
        self._filename = filename
        self._data = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            with open(self._filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if isinstance(v, list):
                        data[k] = ObservableList(v, self._save)
                self._data = data
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {}

    def _save(self):
        with self._lock:
            with open(self._filename, "w", encoding="utf-8") as f:
                # print(f'save {self._data}')
                json.dump(self._data, f, indent=4)

    def __getattr__(self, name):
        # print(f'get [{name}] = {self._data.get(name, None)}')

        return self._data.get(name, None)

    def __setattr__(self, name, value):
        if name in {"_filename", "_data", "_lock", "_save", "_load"}:
            super().__setattr__(name, value)
        else:
            if isinstance(value, list):
                value = ObservableList(value, self._save)
            self._data[name] = value
            # print(f'set [{name}] = {value}')
            self._save()

    def to_dict(self):
        return self._data.copy()
    
class ObservableList(list):
    def __init__(self, initial_list, on_change):
        super().__init__(initial_list)
        self._on_change = on_change

    def append(self, item):
        super().append(item)
        self._on_change()

    def extend(self, iterable):
        super().extend(iterable)
        self._on_change()

    def insert(self, index, item):
        super().insert(index, item)
        self._on_change()

    def remove(self, item):
        super().remove(item)
        self._on_change()

    def pop(self, index=-1):
        item = super().pop(index)
        self._on_change()
        return item

    def clear(self):
        super().clear()
        self._on_change()
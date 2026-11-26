import json
from importlib.resources import files
from dataclasses import dataclass

@dataclass(frozen=True)
class Feature:
    id: str
    name: str
    trigger: str
    implemented: bool
    classification: str

class FeatureRegistry:
    def __init__(self):
        raw=json.loads(files('atof').joinpath('catalog/features.json').read_text(encoding='utf-8'))
        self._features={x['id']:Feature(**x) for x in raw}
        if not self._features or len(self._features) != len(raw):
            raise ValueError('Feature catalog requires nonempty, distinct feature IDs')

    def all(self):
        return list(self._features.values())

    def get(self, identifier):
        return self._features[identifier]

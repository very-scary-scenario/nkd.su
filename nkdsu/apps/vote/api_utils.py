from datetime import datetime
from typing import Protocol, _ProtocolMeta

from django.db.models.base import Model, ModelBase


JsonEncodable = (
    None | bool | int | float | str | datetime | dict[str, 'JsonEncodable'] | list['JsonEncodable']
)
JsonDict = dict[str, JsonEncodable]
JsonList = list[JsonEncodable]


class SerializableModelMeta(_ProtocolMeta, ModelBase):
    pass


class SerializableBase(Protocol, metaclass=SerializableModelMeta):
    def api_dict(self, verbose: bool = False) -> JsonDict: ...


class Serializable(SerializableBase, Model):
    class Meta:
        abstract = True

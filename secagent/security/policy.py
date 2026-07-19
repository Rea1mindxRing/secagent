from enum import Enum


class SafetyMode(Enum):
    STRICT = "strict"
    SMART = "smart"
    YOLO = "yolo"

    @classmethod
    def from_string(cls, value: str) -> "SafetyMode":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.SMART

    @classmethod
    def list_values(cls) -> list:
        return [m.value for m in cls]
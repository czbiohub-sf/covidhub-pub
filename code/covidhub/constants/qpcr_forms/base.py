from dataclasses import dataclass, fields, MISSING


@dataclass(init=False)
class Cols:
    @classmethod
    def columns(cls):
        result = list()
        for f in fields(cls):
            if f.default is not MISSING:
                val = f.default
            elif f.default_factory is not MISSING:
                val = f.default_factory()
            else:
                raise ValueError(f"No default value for column {f}")

            if isinstance(val, tuple) or isinstance(val, list):
                result.extend(val)
            else:
                result.append(val)
        return result


@dataclass(init=False)
class Base(Cols):
    TIMESTAMP: str = "timestamp"
    RESEARCHER_NAME: str = "researcher_name"
    NOTES: str = "notes"

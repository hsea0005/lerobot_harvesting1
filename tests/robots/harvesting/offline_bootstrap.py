"""Offline-only substitutes for external imports, never for LeRobot source or device logic.

This does NOT validate real draccus CLI parsing, SDK packets, Torch, training or inference.
Use verify_install.py and the normal test suite in a fully installed environment for those imports.
"""

import dataclasses
import importlib.machinery
import json
import sys
import tempfile
import types
from contextlib import nullcontext
from pathlib import Path
from typing import get_args, get_origin


def install() -> None:
    class ChoiceRegistry:
        _choices = {}

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            cls._choices = {}

        @classmethod
        def register_subclass(cls, name):
            def register(subclass):
                cls._choices[name] = subclass
                return subclass
            return register

        @classmethod
        def get_choice_name(cls, subclass):
            for base in cls.__mro__:
                for name, candidate in getattr(base, "_choices", {}).items():
                    if candidate is subclass:
                        return name
            raise ValueError(subclass)

        @classmethod
        def get_known_choices(cls):
            return cls._choices

    def module(name, package=False):
        value = types.ModuleType(name)
        value.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=package)
        if package:
            value.__path__ = []
        sys.modules[name] = value
        return value

    numpy = module("numpy", True)
    # Offline camera tests check shape only; no image or numerical computation is simulated.
    numpy.ndarray = type("ndarray", (), {"__class_getitem__": classmethod(lambda cls, item: cls)})
    numpy.uint8 = type("uint8", (), {})
    numpy.zeros = lambda shape, dtype=None: types.SimpleNamespace(shape=shape, dtype=dtype)
    module("numpy.typing").NDArray = numpy.ndarray

    draccus = module("draccus", True)
    draccus.ChoiceRegistry = ChoiceRegistry
    choice_types = module("draccus.choice_types")
    choice_types.ChoiceRegistry = ChoiceRegistry
    draccus.config_type = lambda _: nullcontext()
    def encode(value):
        if dataclasses.is_dataclass(value):
            return dataclasses.asdict(value)
        raise TypeError(type(value))
    draccus.dump = lambda value, file, **kwargs: json.dump(value, file, default=encode, **kwargs)
    def load(kind, file):
        data = json.load(file)
        if get_origin(kind) is dict:
            value_type = get_args(kind)[1]
            return {key: value_type(**value) for key, value in data.items()}
        return kind(**data)
    draccus.load = load
    # RobotAction annotations only: no numerical Torch operation is exercised.
    torch = module("torch")
    torch.Tensor = type("Tensor", (), {})
    torch.device = type("device", (), {})
    torch.dtype = type("dtype", (), {})
    for name in ["bfloat16", "float16", "float32", "float64", "int64"]:
        setattr(torch, name, torch.dtype())
    torch.__version__ = "offline-import-only"
    progress = module("tqdm")
    progress.tqdm = lambda iterable, **kwargs: iterable
    module("huggingface_hub", True)
    constants = module("huggingface_hub.constants")
    constants.HF_HOME = str(Path(tempfile.gettempdir()) / "harvesting-offline-tests")

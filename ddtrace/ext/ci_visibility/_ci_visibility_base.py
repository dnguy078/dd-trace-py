import abc
import dataclasses
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import TypeVar
from typing import Union

from ddtrace.internal.logger import get_logger


log = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class _CISessionId:
    """Placeholder ID without attributes

    Allows reusing the same _CIVisibilityAPIBase methods for sessions which do not have individual session IDs
    """


@dataclasses.dataclass(frozen=True)
class _CIVisibilityRootItemIdBase:
    """This class exists for the ABC class below"""

    name: str

    def get_parent_id(self) -> "_CIVisibilityRootItemIdBase":
        return self


RT = TypeVar("RT", bound="_CIVisibilityRootItemIdBase")


@dataclasses.dataclass(frozen=True)
class _CIVisibilityIdBase(abc.ABC):
    @abc.abstractmethod
    def get_parent_id(self) -> Union["_CIVisibilityIdBase", _CIVisibilityRootItemIdBase]:
        raise NotImplementedError("This method must be implemented by the subclass")


PT = TypeVar("PT", bound=Union[_CIVisibilityIdBase, _CIVisibilityRootItemIdBase])


@dataclasses.dataclass(frozen=True)
class _CIVisibilityChildItemIdBase(_CIVisibilityIdBase, Generic[PT]):
    parent_id: PT
    name: str

    def get_parent_id(self) -> PT:
        return self.parent_id


CIItemId = TypeVar("CIItemId", bound=Union[_CIVisibilityChildItemIdBase, _CIVisibilityRootItemIdBase, _CISessionId])


class _CIVisibilityAPIBase(abc.ABC):
    class GetTagArgs(NamedTuple):
        item_id: Union[_CIVisibilityChildItemIdBase, _CIVisibilityRootItemIdBase, _CISessionId]
        name: str

    class SetTagArgs(NamedTuple):
        item_id: Union[_CIVisibilityChildItemIdBase, _CIVisibilityRootItemIdBase, _CISessionId]
        name: str
        value: Any

    class DeleteTagArgs(NamedTuple):
        item_id: Union[_CIVisibilityChildItemIdBase, _CIVisibilityRootItemIdBase, _CISessionId]
        name: str

    class SetTagsArgs(NamedTuple):
        item_id: Union[_CIVisibilityChildItemIdBase, _CIVisibilityRootItemIdBase, _CISessionId]
        tags: Dict[str, Any]

    class DeleteTagsArgs(NamedTuple):
        item_id: Union[_CIVisibilityChildItemIdBase, _CIVisibilityRootItemIdBase, _CISessionId]
        names: List[str]

    def __init__(self):
        raise NotImplementedError("This class is not meant to be instantiated")

    @staticmethod
    @abc.abstractmethod
    def discover(item_id: CIItemId, *args, **kwargs):
        pass

    @staticmethod
    @abc.abstractmethod
    def start(item_id: CIItemId, *args, **kwargs):
        pass

    @staticmethod
    @abc.abstractmethod
    def finish(
        item_id: _CIVisibilityRootItemIdBase,
        override_status: Optional[Enum],
        force_finish_children: bool = False,
        *args,
        **kwargs,
    ):
        pass


@dataclasses.dataclass(frozen=True)
class CISourceFileInfoBase:
    """This supplies the __post_init__ method for the CISourceFileInfo

    It is simply here for cosmetic reasons of keeping the original class definition short
    """

    path: Path
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    def __post_init__(self):
        """Enforce that attributes make sense after initialization"""
        self._check_path()
        self._check_line_numbers()

    def _check_path(self):
        """Checks that path is of Path type and is absolute, converting it to absolute if not"""
        if not isinstance(self.path, Path):
            raise ValueError("path must be a Path object, but is of type %s", type(self.path))

        if not self.path.is_absolute():
            abs_path = self.path.absolute()
            log.debug("Converting path to absolute: %s -> %s", self.path, abs_path)
            object.__setattr__(self, "path", abs_path)

    def _check_line_numbers(self):
        self._check_line_number("start_line")
        self._check_line_number("end_line")

        # Lines must be non-zero positive ints after _check_line_number ran
        if self.start_line is not None and self.end_line is not None:
            if self.start_line > self.end_line:
                raise ValueError("start_line must be less than or equal to end_line")

        if self.start_line is None and self.end_line is not None:
            raise ValueError("start_line must be set if end_line is set")

    def _check_line_number(self, attr_name: str):
        """Checks that a line number is a positive integer, setting to None if not"""
        line_number = getattr(self, attr_name)

        if line_number is None:
            return

        if not isinstance(line_number, int):
            raise ValueError("%s must be an integer, but is of type %s", attr_name, type(line_number))

        if line_number < 1:
            raise ValueError("%s must be a positive integer, but is %s", attr_name, line_number)

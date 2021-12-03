from enum import Enum
from typing import Iterator, Optional

from argo_workflow_tools.dsl.parameter_builders import ParameterBuilder


class SourceType(Enum):
    PARAMETER = "parameter"
    NODE_OUTPUT = "node_output"
    REDUCE = "reduce"
    PARTITION = "partition"
    PARTITION_OUTPUT = "partition_output"
    KEY = "key"
    PROPERTY = "property"
    BRANCH = "branch"


class InputDefinition:
    def __init__(
        self,
        source_type: SourceType,
        name: str,
        source_node_id: str = None,
        references: Optional["InputDefinition"] = None,
        parameter_builder: ParameterBuilder = None,
        key_name: str = None,
    ):
        self.source_type = source_type
        self.name = name
        self.source_node_id = source_node_id
        self.reference = references
        self.parameter_builder = parameter_builder
        self.key_name = key_name

    @property
    def is_node_output(self):
        return self.source_node_id is not None

    @property
    def is_partition(self):
        if self.source_type == SourceType.PARTITION:
            return True
        if self.source_type == SourceType.REDUCE:
            return False
        elif self.reference:
            return self.reference.is_partition
        else:
            return False

    @property
    def key_path(self):
        if (
            self.source_type == SourceType.KEY
            or self.source_type == SourceType.PROPERTY
        ):
            key_path = self.reference.key_path
            if key_path:
                return ".".join([key_path, self.key_name])
            else:
                return self.key_name
        else:
            return None

    @property
    def partition_source(self):
        if self.is_partition:
            return self.reference.partition_source
        else:
            return self

    def __iter__(self) -> Iterator:
        return iter(
            [
                InputDefinition(
                    source_type=SourceType.PARTITION,
                    name=self.name,
                    source_node_id=self.source_node_id,
                    references=self,
                )
            ]
        )

    def __getitem__(self, name) -> "InputDefinition":
        if (
            self.source_type == SourceType.KEY
            or self.source_type == SourceType.PROPERTY
        ):
            raise ValueError(
                f"You are trying to call item '{name}' under '{self.key_name}'. "
                f"Argo allows only one level of field extraction"
            )
        return InputDefinition(
            source_type=SourceType.KEY,
            name=self.name,
            source_node_id=self.source_node_id,
            references=self,
            key_name=name,
        )

    def __getattr__(self, name) -> "InputDefinition":
        if name.startswith("__") and name.endswith("__"):
            raise ValueError(
                f"You are trying to reference attribute '{name}'. Argo does not support special methods"
            )
        return InputDefinition(
            source_type=SourceType.PROPERTY,
            name=self.name,
            source_node_id=self.source_node_id,
            references=self,
            key_name=name,
        )

    def __repr__(self):
        return f"InputDefinition(source_type={self.source_type.name} name={self.name} source_node_id={self.source_node_id})"

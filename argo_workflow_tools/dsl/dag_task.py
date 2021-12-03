from dataclasses import dataclass
from typing import Callable, Mapping, Union

from argo_workflow_tools.dsl.node_output import InputDefinition
from argo_workflow_tools.dsl.node_properties import (
    DAGNodeProperties,
    TaskNodeProperties,
)


@dataclass
class NodeReference(object):
    """
    Represents a result referece from a called node
    """

    id: str
    name: str
    outputs: [InputDefinition]
    func: Callable
    node: str
    arguments: Mapping[str, Union[InputDefinition]]
    wait_for: list[InputDefinition]


@dataclass
class DAGReference(NodeReference):
    """
    Represents a result referece from a called DAG
    """

    properties: DAGNodeProperties


@dataclass
class TaskReference(NodeReference):
    """
    Represents a result referece from a called task
    """

    properties: TaskNodeProperties

    def __repr__(self):
        return f"TaskReference(name={self.name} id={self.id})"

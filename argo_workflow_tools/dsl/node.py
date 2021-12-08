import inspect
from abc import abstractmethod
from typing import Any, Callable, Dict, Iterable, Mapping, Sequence, cast

from argo_workflow_tools.dsl import building_mode_context as context
from argo_workflow_tools.dsl.dag_task import DAGReference, TaskReference
from argo_workflow_tools.dsl.input_definition import InputDefinition, SourceType
from argo_workflow_tools.dsl.node_properties.dag_node_properties import (
    DAGNodeProperties,
)
from argo_workflow_tools.dsl.node_properties.task_node_properties import (
    TaskNodeProperties,
)
from argo_workflow_tools.dsl.parameter_builders.default_parameter_builder import (
    DefaultParameterBuilder,
)
from argo_workflow_tools.dsl.utils.utils import sanitize_name, uuid_short
from argo_workflow_tools.dsl.workflow_template_collector import (
    add_task,
    collect_conditions,
)


class Node(object):
    def __init__(self, func: Callable, **kwargs):
        """

        Parameters
        ----------
        func :
        kwargs :
        """
        self._func = func
        self.kwargs = kwargs

    @property
    def func(self) -> Callable:
        """

        Returns
        -------

        """
        return self._func

    @abstractmethod
    def __call__(self, *args, **kwargs) -> Any:
        """

        Returns
        -------
        object
        """
        pass

    @staticmethod
    def _filter_dag_args(kwargs: Dict) -> Dict:
        """
        Filters out parameters used internally to genrate control flows
        Parameters
        ----------
        kwargs : parameter dictionary

        Returns
        -------
        filtered parameter dictionary
        """
        filtered_kwargs = kwargs.copy()
        filtered_kwargs.pop("wait_for", None)
        filtered_kwargs.pop("when", None)
        return filtered_kwargs

    @staticmethod
    def _get_wait(kwargs) -> list["str"]:
        """
        Generaete dependecy out of wait_for parameter
        Parameters
        ----------
        kwargs :
            fucntion argumetns
        Returns
        -------
            list of dependencies

        """
        if not kwargs.get("wait_for"):
            return []
        dependencies = cast(InputDefinition, kwargs.get("wait_for"))
        if (
            isinstance(dependencies, InputDefinition) and dependencies.is_node_output
        ):  # TODO or it's variants NODE_OUTPUT
            return [dependencies]
        if isinstance(dependencies, Iterable):
            return list(
                filter(
                    lambda dependency: dependency.source_type == SourceType.NODE_OUTPUT,
                    dependencies,
                )
            )

    @staticmethod
    def _reduce_fan_in_arguments(name: str, arg: Any) -> Any:
        if (
            isinstance(arg, Sequence)
            and len(arg) == 1
            and isinstance(arg[0], InputDefinition)
            and arg[0].is_node_output
            and arg[0].reference
        ):
            return InputDefinition(
                SourceType.REDUCE,
                name=sanitize_name(arg[0].name),
                source_node_id=arg[0].source_node_id,
                references=arg[0],
            )

        if isinstance(arg, Sequence) and any([item.is_node_output for item in arg]):
            raise ValueError(
                f"Argument '{name}' of type '{type(arg).__name__}' is invalid. it mixes both parameters and node outputs"
            )

        return arg

    def _bind_arguments(self, *args, **kwargs) -> Mapping[str, Any]:
        signature = inspect.signature(self._func)
        kwargs_filtered = self._filter_dag_args(kwargs)
        try:
            bound_args = signature.bind(*args, **kwargs_filtered)
            arguments = {**bound_args.arguments}
        except TypeError as e:
            raise TypeError(
                f"You have invoked the task '{self._func.__name__}' with signature '{signature}' "
                f"with : args=({str.join(',', map(lambda arg: arg.name, args))}) kwargs=({str.join(',', kwargs.keys())}). "
                f"{e}."
            ) from e

        kwarg_parameters = [
            name
            for name, param in signature.parameters.items()
            if param.kind == inspect.Parameter.VAR_KEYWORD
        ]
        for kwarg_param_name in kwarg_parameters:
            arguments = {**arguments, **arguments[kwarg_param_name]}
            del arguments[kwarg_param_name]

        return {k: self._reduce_fan_in_arguments(k, v) for k, v in arguments.items()}

    @staticmethod
    def _arguments(arguments: Mapping[str, Any]) -> Mapping[str, InputDefinition]:
        return {
            argument_name: argument_value
            for argument_name, argument_value in arguments.items()
            if isinstance(argument_value, InputDefinition)
        }


class DAGNode(Node):
    def __init__(self, func: Callable, properties: DAGNodeProperties):
        """
        reporesents a DAG node in the workflow graph
        Parameters
        ----------
        func : function describing the DAG
        properties : argo properties for DAG
        """
        super().__init__(func)
        self.properties = properties

    def __call__(self, *args, **kwargs) -> Any:
        """
        call the DAG function, in case we are not in DSL compilation mode, the function will call the function.
        else the fucntion will return a reference response representing the node response
        """
        if not context.dag_building_mode.get():
            cleaned_kwargs = self._filter_dag_args(kwargs)
            conditions = collect_conditions()
            if all([condition.value for condition in conditions]):
                return self._func(*args, **cleaned_kwargs)
            else:
                return None

        guid = sanitize_name(self._func.__name__) + "-" + uuid_short()

        arguments = self._bind_arguments(*args, **kwargs)
        partitioned_arguments = list(
            filter(lambda argument: argument.is_partition, arguments.values())
        )
        if len(partitioned_arguments) > 1:
            raise ValueError(
                "Nested loops are not allowed in the same DAG, split your loops into nested DAG's instead"
            )
        output = InputDefinition(
            source_type=SourceType.NODE_OUTPUT, source_node_id=guid, name="result"
        )
        conditions = collect_conditions()

        add_task(
            DAGReference(
                id=guid,
                name=sanitize_name(self._func.__name__),
                func=self._func,
                wait_for=self._get_wait(kwargs),
                arguments=self._arguments(arguments),
                outputs=[output],
                node=self,
                properties=self.properties,
                conditions=conditions,
            ),
        )

        return output


class TaskNode(Node):
    def __init__(self, func: Callable, properties: TaskNodeProperties):
        """
        reporesents a task leaf node in the workflow graph
        Parameters
        ----------
        func : function describing the task
        properties : argo properties for task
        """
        super().__init__(func)
        self.properties = properties

    def __call__(self, *args, **kwargs) -> Any:
        """
        call the DAG function, in case we are not in DSL compilation mode, the function will call the function.
        else the fucntion will return a reference response representing the node response
        """
        if not context.dag_building_mode.get():
            cleaned_kwargs = self._filter_dag_args(kwargs)
            conditions = collect_conditions()
            if all([condition.value for condition in conditions]):
                return self._func(*args, **cleaned_kwargs)
            else:
                return None

        arguments = self._bind_arguments(*args, **kwargs)
        partitioned_arguments = list(
            filter(lambda argument: argument.is_partition, arguments.values())
        )
        if len(partitioned_arguments) > 1:
            raise ValueError(
                "Nested loops are not allowed in the same DAG, split your loops into nested DAG's instead"
            )
        guid = sanitize_name(self._func.__name__) + "-" + uuid_short()
        conditions = [
            condition.condition_string() for condition in collect_conditions()
        ]
        if partitioned_arguments:
            output = InputDefinition(
                source_type=SourceType.NODE_OUTPUT,
                source_node_id=guid,
                name=sanitize_name("result"),
                references=partitioned_arguments,
                parameter_builder=DefaultParameterBuilder(None),
            )
        else:
            output = InputDefinition(
                source_type=SourceType.NODE_OUTPUT,
                source_node_id=guid,
                name=sanitize_name("result"),
                parameter_builder=DefaultParameterBuilder(None),
            )

        add_task(
            TaskReference(
                id=guid,
                name=sanitize_name(self._func.__name__),
                func=self._func,
                wait_for=self._get_wait(kwargs),
                arguments=self._arguments(arguments),
                outputs=output,
                properties=self.properties,
                node=self,
                conditions=conditions,
            ),
        )
        return output

from copy import deepcopy
from typing import Any, Iterable, List, Optional, Union, Sequence
from uuid import uuid4

from fedot.core.dag.graph import Graph
from fedot.core.dag.graph_node import GraphNode
from fedot.core.dag.graph_operator import GraphOperator
from fedot.core.dag.node_operator import NodeOperator
from fedot.core.log import Log, default_log
from fedot.core.utilities.data_structures import UniqueList
from fedot.core.utils import DEFAULT_PARAMS_STUB
from fedot.core.visualisation.graph_viz import GraphVisualiser


def node_ops_adaptation(func):
    def _adapt(adapter, node: Any):
        if not isinstance(node, OptNode):
            return adapter.adapt(node)
        return node

    def _decorator(self, *args, **kwargs):
        func_result = func(self, *args, **kwargs)
        self.nodes = [_adapt(self._node_adapter, node) for node in self.nodes]
        return func_result

    return _decorator


OptNode = GraphNode


class OptGraph(Graph):
    """
    Base class used for optimized structure

    :param nodes: OptNode object(s)
    :param log: Log object to record messages
    """

    def __init__(self, nodes: Union[OptNode, List[OptNode]] = (),
                 log: Optional[Log] = None):
        self.log = log or default_log(__name__)
        self.operator = GraphOperator(nodes)

    @property
    def nodes(self) -> List[OptNode]:
        return self.operator.nodes

    @nodes.setter
    def nodes(self, new_nodes: List[OptNode]):
        self.operator.nodes = new_nodes

    @property
    def _node_adapter(self):
        return NodeOperatorAdapter()

    @node_ops_adaptation
    def add_node(self, new_node: OptNode):
        """
        Add new node to the OptGraph

        :param new_node: new OptNode object
        """
        self.operator.add_node(self._node_adapter.restore(new_node))

    @node_ops_adaptation
    def update_node(self, old_node: OptNode, new_node: OptNode):
        """
        Replace old_node with new one.

        :param old_node: OptNode object to replace
        :param new_node: OptNode object to replace
        """

        self.operator.update_node(self._node_adapter.restore(old_node),
                                  self._node_adapter.restore(new_node))

    @node_ops_adaptation
    def update_subtree(self, old_subroot: OptNode, new_subroot: OptNode):
        """
        Replace the subtrees with old and new nodes as subroots

        :param old_subroot: OptNode object to replace
        :param new_subroot: OptNode object to replace
        """
        self.operator.update_subtree(self._node_adapter.restore(old_subroot),
                                     self._node_adapter.restore(new_subroot))

    @node_ops_adaptation
    def delete_node(self, node: OptNode):
        """
        Delete chosen node redirecting all its parents to the child.

        :param node: OptNode object to delete
        """

        self.operator.delete_node(self._node_adapter.restore(node))

    @node_ops_adaptation
    def delete_subtree(self, subroot: OptNode):
        """
        Delete the subtree with node as subroot.

        :param subroot:
        """
        self.operator.delete_subtree(self._node_adapter.restore(subroot))

    def show(self, path: str = None):
        GraphVisualiser().visualise(self, path)

    def __eq__(self, other) -> bool:
        return self.operator.__eq__(other)

    def __str__(self):
        return str(self.operator.graph_description)

    def __repr__(self):
        return self.__str__()

    @property
    def root_node(self):
        roots = self.operator.root_node
        return roots

    @property
    def descriptive_id(self):
        return self.operator.descriptive_id

    @property
    def length(self) -> int:
        return len(self.nodes)

    @property
    def depth(self) -> int:
        return self.operator.depth

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        return result

    def __deepcopy__(self, memo=None):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result


class NodeOperatorAdapter:
    def adapt(self, adaptee) -> OptNode:
        adaptee.__class__ = OptNode
        return adaptee

    def restore(self, node) -> GraphNode:
        obj = node
        obj.__class__ = GraphNode
        return obj

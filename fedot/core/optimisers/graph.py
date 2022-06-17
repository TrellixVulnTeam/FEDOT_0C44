from os import PathLike
from copy import deepcopy
from typing import Any, Callable, Iterable, List, Optional, Union, Sequence, Tuple
from uuid import uuid4

from fedot.core.dag.graph import Graph
from fedot.core.dag.graph_node import GraphNode
from fedot.core.dag.graph_operator import GraphOperator
from fedot.core.dag.node_operator import NodeOperator
from fedot.core.log import default_log
from fedot.core.utilities.data_structures import UniqueList, ensure_wrapped_in_sequence
from fedot.core.utils import DEFAULT_PARAMS_STUB, copy_doc
from fedot.core.visualisation.graph_viz import GraphVisualiser, NodeColorType


def node_ops_adaptation(func: Callable) -> Callable:
    def _adapt(adapter, node: Any) -> OptNode:
        if not isinstance(node, OptNode):
            return adapter.adapt(node)
        return node

    def _decorator(self, *args, **kwargs) -> Any:
        func_result = func(self, *args, **kwargs)
        self.nodes = [_adapt(self._node_adapter, node) for node in self.nodes]
        return func_result

    return _decorator


OptNode = GraphNode


class OptGraph(Graph):
    """Base class used for optimized structure

    :param nodes: optimization graph nodes object(s)
    """

    def __init__(self, nodes: Union[OptNode, List[OptNode]] = ()):
        self.log = default_log(self)
        self.operator = GraphOperator(nodes)

    @property
    def nodes(self) -> List[OptNode]:
        return self.operator.nodes

    @nodes.setter
    def nodes(self, new_nodes: List[OptNode]):
        self.operator.nodes = new_nodes

    @property
    def _node_adapter(self):
        """Creates node operator adapter class instance and returns it

        :return: new instance of :class:`~fedot.core.optimisers.graph.NodeOperatorAdapter`
        """
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

    def distance_to_root_level(self, node: OptNode) -> int:
        """ Returns distance to root level """
        return self.operator.distance_to_root_level(node=self._node_adapter.restore(node))

    def nodes_from_layer(self, layer_number: int) -> List[Any]:
        """ Returns all nodes from specified layer """
        return self.operator.nodes_from_layer(layer_number=layer_number)

    @node_ops_adaptation
    def node_children(self, node: OptNode) -> List[Optional[OptNode]]:
        """ Returns all node's children """
        return self.operator.node_children(node=self._node_adapter.restore(node))

    @node_ops_adaptation
    def connect_nodes(self, node_parent: OptNode, node_child: OptNode):
        """ Add an edge from node_parent to node_child """
        self.operator.connect_nodes(parent=self._node_adapter.restore(node_parent),
                                    child=self._node_adapter.restore(node_child))

    @node_ops_adaptation
    def disconnect_nodes(self, node_parent: OptNode, node_child: OptNode,
                         clean_up_leftovers: bool = True):
        """ Delete an edge from node_parent to node_child """
        self.operator.disconnect_nodes(node_parent=self._node_adapter.restore(node_parent),
                                       node_child=self._node_adapter.restore(node_child),
                                       clean_up_leftovers=clean_up_leftovers)

    def get_nodes_degrees(self):
        """ Nodes degree as the number of edges the node has:
         k = k(in) + k(out) """
        return self.operator.get_nodes_degrees()

    def get_edges(self):
        """ Returns all available edges in a given graph """
        return self.operator.get_edges()

    @copy_doc(Graph.show)
    def show(self, save_path: Optional[Union[PathLike, str]] = None, engine: str = 'matplotlib',
             node_color: Optional[NodeColorType] = None, dpi: int = 300,
             node_size_scale: float = 1.0, font_size_scale: float = 1.0, edge_curvature_scale: float = 1.0):
        GraphVisualiser().visualise(self, save_path, engine, node_color, dpi, node_size_scale,
                                    font_size_scale, edge_curvature_scale)

    def __eq__(self, other) -> bool:
        return self.operator.__eq__(other)

    def __str__(self):
        return str(self.operator.graph_description)

    @copy_doc(Graph.__repr__)
    def __repr__(self):
        return self.__str__()

    @property
    def root_node(self):
        roots = self.operator.root_node
        return roots

    @property
    @copy_doc(GraphOperator.descriptive_id)
    def descriptive_id(self) -> str:
        return self.operator.descriptive_id

    @property
    @copy_doc(Graph.length)
    def length(self) -> int:
        return len(self.nodes)

    @property
    @copy_doc(Graph.depth)
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

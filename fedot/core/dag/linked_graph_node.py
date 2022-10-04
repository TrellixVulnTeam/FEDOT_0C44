from typing import Union, Optional, Iterable, List
from uuid import uuid4

from fedot.core.dag.graph_node import GraphNode
from fedot.core.utilities.data_structures import UniqueList
from fedot.core.utils import DEFAULT_PARAMS_STUB


class LinkedGraphNode(GraphNode):
    """Class for node definition in the directed graph structure
    that directly stores its parent nodes.

    Args:
        nodes_from: parent nodes which information comes from
        content: ``dict`` for the content in the node

    Notes:
        The possible parameters are:
            - ``name`` - name (str) or object that performs actions in this node
            - ``params`` - dictionary with additional information that is used by
                    the object in the ``name`` field (e.g. hyperparameters values)
    """

    def __init__(self, content: Union[dict, str],
                 nodes_from: Optional[Iterable['LinkedGraphNode']] = None):
        # Wrap string into dict if it is necessary
        if isinstance(content, str):
            content = {'name': content}

        self.content = content
        self._nodes_from = UniqueList(nodes_from or ())
        self.uid = str(uuid4())

    @property
    def nodes_from(self) -> List['LinkedGraphNode']:
        return self._nodes_from

    @nodes_from.setter
    def nodes_from(self, nodes: Optional[Iterable['LinkedGraphNode']]):
        self._nodes_from = UniqueList(nodes)

    def __hash__(self) -> int:
        return hash(self.uid)

    def __str__(self) -> str:
        return str(self.content['name'])

    def __repr__(self) -> str:
        return self.__str__()

    def description(self) -> str:
        node_operation = self.content['name']
        params = self.content.get('params')
        # TODO: possibly unify with __repr__ & don't duplicate Operation.description
        if isinstance(node_operation, str):
            # If there is a string: name of operation (as in json repository)
            if params and params != DEFAULT_PARAMS_STUB:
                node_label = f'n_{node_operation}_{params}'
            else:
                node_label = f'n_{node_operation}'
        else:
            # If instance of Operation is placed in 'name'
            node_label = node_operation.description(params)
        return node_label

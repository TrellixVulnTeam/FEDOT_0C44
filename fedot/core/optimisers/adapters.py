from typing import Any, Optional, Dict

from fedot.core.adapter import BaseOptimizationAdapter
from fedot.core.dag.graph_node import map_nodes
from fedot.core.optimisers.graph import OptGraph, OptNode
from fedot.core.pipelines.node import PrimaryNode, SecondaryNode, Node
from fedot.core.pipelines.pipeline import Pipeline


class PipelineAdapter(BaseOptimizationAdapter[Pipeline]):
    """Optimization adapter for Pipeline<->OptGraph translation.
    It does 2 things:
    - on restore: build Pipeline Nodes from information stored in OptNodes
    - on adapt: clear OptGraph from metadata and 'heavy' data (like fitted models)
    """

    def __init__(self):
        super().__init__(base_graph_class=Pipeline)

    @staticmethod
    def _transform_to_opt_node(node: Node) -> OptNode:
        # Prepare content for nodes
        content = {'name': str(node.operation),
                   'params': node.custom_params,
                   'metadata': node.metadata}
        return OptNode(content)

    @staticmethod
    def _transform_to_pipeline_node(node: OptNode) -> Node:
        if not node.nodes_from:
            return PrimaryNode(operation_type=node.content['name'], content=node.content)
        else:
            return SecondaryNode(operation_type=node.content['name'], content=node.content,
                                 nodes_from=node.nodes_from)

    def _adapt(self, adaptee: Pipeline) -> OptGraph:
        adapted_nodes = map_nodes(self._transform_to_opt_node, adaptee.nodes)
        return OptGraph(adapted_nodes)

    def _restore(self, opt_graph: OptGraph, metadata: Optional[Dict[str, Any]] = None) -> Pipeline:
        restored_nodes = map_nodes(self._transform_to_pipeline_node, opt_graph.nodes)
        pipeline = Pipeline(restored_nodes)

        metadata = metadata or {}
        pipeline.computation_time = metadata.get('computation_time_in_seconds')
        return pipeline

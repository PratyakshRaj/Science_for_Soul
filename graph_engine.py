from typing import Dict
from models import ConceptNode

# This is exactly where your global graph state lives!
CONCEPT_GRAPH: Dict[str, ConceptNode] = {}

def causes_cycle(graph: Dict[str, ConceptNode], start_node: str, target_node: str) -> bool:
    if target_node not in graph:
        return False
    queue = list(graph[target_node].prerequisites)
    visited = set()
    while queue:
        current = queue.pop(0)
        if current == start_node:
            return True  
        if current not in visited:
            visited.add(current)
            if current in graph:
                queue.extend(graph[current].prerequisites)
    return False

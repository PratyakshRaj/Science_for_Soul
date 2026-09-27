from fastapi import FastAPI, HTTPException, status
from typing import Dict, List
from models import ConceptNode
from graph_engine import CONCEPT_GRAPH, causes_cycle

app = FastAPI(
    title="AI Coach - Dynamic Prerequisite Graph Test API",
    description="API to test concept node creation, validation, and cycle detection.",
    version="1.0.0"
)

@app.post("/concepts", status_code=status.HTTP_201_CREATED, response_model=ConceptNode)
def create_concept(node: ConceptNode):
    """
    Creates or updates a concept node in the global graph.
    Validates that prerequisites exist and do not introduce cycles.
    """
    # 1. Check if the node ID already exists (optional warning/overwrite behavior)
    # For testing, we allow updating an existing node or creating a new one.
    
    # 2. Validate that all declared prerequisites actually exist in the graph
    for prereq_id in node.prerequisites:
        if prereq_id not in CONCEPT_GRAPH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prerequisite node '{prereq_id}' does not exist in the graph. Create it first."
            )
        
        # 3. Check for cycles: adding 'prereq_id' as a prerequisite to 'node.id'
        if causes_cycle(CONCEPT_GRAPH, start_node=node.id, target_node=prereq_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add prerequisite '{prereq_id}'. It introduces a circular dependency cycle."
            )

    # 4. Save to global state
    CONCEPT_GRAPH[node.id] = node
    return node


@app.get("/concepts", response_model=Dict[str, ConceptNode])
def get_all_concepts():
    """
    Returns the complete global graph state.
    """
    return CONCEPT_GRAPH


@app.get("/concepts/{concept_id}", response_model=ConceptNode)
def get_concept(concept_id: str):
    """
    Retrieves a single concept node by its unique ID.
    """
    if concept_id not in CONCEPT_GRAPH:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept node '{concept_id}' not found."
        )
    return CONCEPT_GRAPH[concept_id]


@app.post("/concepts/seed", status_code=status.HTTP_200_OK)
def seed_sample_data():
    """
    Seeds the graph with sample JEE data from your architecture plan
    (Vectors -> System of Particles -> Rotational Mechanics).
    """
    CONCEPT_GRAPH.clear()
    
    # Base concept
    vectors = ConceptNode(
        id="vectors",
        title="Vectors",
        description="Introduction to vectors and cross products.",
        content={"video_links": [], "proofs": [], "examples": []},
        prerequisites=[]
    )
    
    # Dependent concept 1
    particles = ConceptNode(
        id="system_of_particles",
        title="System of Particles",
        description="Center of mass and basic particle dynamics.",
        content={"video_links": [], "proofs": [], "examples": []},
        prerequisites=["vectors"]
    )
    
    # Dependent concept 2
    rotational = ConceptNode(
        id="rotational_mechanics",
        title="Rotational Mechanics",
        description="Torque, angular momentum, and rigid body dynamics.",
        content={"video_links": [], "proofs": [], "examples": []},
        prerequisites=["system_of_particles"]
    )
    
    CONCEPT_GRAPH["vectors"] = vectors
    CONCEPT_GRAPH["system_of_particles"] = particles
    CONCEPT_GRAPH["rotational_mechanics"] = rotational
    
    return {"message": "Graph successfully seeded with basic JEE physics pipeline.", "current_keys": list(CONCEPT_GRAPH.keys())}


@app.delete("/concepts", status_code=status.HTTP_204_NO_CONTENT)
def clear_graph():
    """
    Resets the global graph state for testing.
    """
    CONCEPT_GRAPH.clear()
    return None

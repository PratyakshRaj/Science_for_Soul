from pydantic import BaseModel
from typing import List

class NodeContent(BaseModel):
    video_links: List[str] = []
    proofs: List[str] = []         
    examples: List[str] = []       

class ConceptNode(BaseModel):
    id: str                        
    title: str                     
    description: str
    content: NodeContent
    question_ids: List[str] = []   
    prerequisites: List[str] = []  

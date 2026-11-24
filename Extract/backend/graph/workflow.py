
from langgraph.graph import StateGraph, START, END

from Extract.backend.graph.state import AdvertisementState
from Extract.backend.nodes.ocr_node import ocr_node
from Extract.backend.nodes.extraction_node import extraction_node
from Extract.backend.nodes.validation_node import validation_node

# Build workflow
graph = StateGraph(AdvertisementState)

# Nodes
graph.add_node("ocr", ocr_node)
graph.add_node("extraction", extraction_node)
graph.add_node("validation", validation_node)


# Connect nodes
graph.add_edge(START, "ocr")
graph.add_edge("ocr", "extraction")
graph.add_edge("extraction", "validation")
graph.add_edge("validation", END)


# Compile workflow
advertisement_workflow = graph.compile()

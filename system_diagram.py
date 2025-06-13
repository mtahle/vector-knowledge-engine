from diagrams import Diagram, Cluster, Edge
from diagrams.azure.storage import BlobStorage
from diagrams.azure.compute import FunctionApps
from diagrams.saas.chat import Slack
from diagrams.onprem.client import Client
from diagrams.programming.framework import FastAPI
from diagrams.azure.analytics import Databricks
from diagrams.generic.storage import Storage
from diagrams.azure.integration import LogicApps
from diagrams.onprem.queue import Kafka
from diagrams.generic.database import SQL

# Modern Azure-style diagram attributes
graph_attr = {
    "fontsize": "24",
    "bgcolor": "gray95:gray90",  # Light gray gradient
    "splines": "curved",  # Modern curved connections
    "nodesep": "1.2",     # More spacing between nodes
    "ranksep": "1.5",     # More vertical spacing
    "pad": "2.0",         # More padding
    "fontname": "Arial",
    "fontcolor": "#252525",
    "style": "rounded,filled",
    "pencolor": "#0078D4",
    "gradientangle": "270"  # Top to bottom gradient
}

# Modern node styling
node_attr = {
    "fontsize": "12",
    "fontname": "Arial",
    "fontcolor": "#252525",
    "width": "0.8",
    "height": "0.8",
    "imagescale": "true",
    "penwidth": "2",
    "margin": "10"
}

# Modern edge styling
edge_attr = {
    "color": "#0078D4",    # Azure blue
    "penwidth": "2",
    "fontname": "Arial",
    "fontsize": "11",
    "fontcolor": "#666666"
}

with Diagram(
    "Vector Knowledge Engine - AI-Powered Semantic Search",
    show=False,
    direction="LR",
    filename="system_architecture",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr
):
    # Data Sources
    with Cluster("Data Sources"):
        knowledge_bases = Client("Knowledge\nBases")
        documents = Storage("Document\nRepositories")
        databases = SQL("Structured\nData")
        archives = Storage("Content\nArchives")

    # Data Ingestion & Scheduling
    with Cluster("Data Ingestion & Processing"):
        scheduler = LogicApps("Periodic\nSync")
        queue = Kafka("Event\nQueue")
        extractor = FastAPI("Data\nExtractor")

    # AI Pipeline
    with Cluster("Vector Processing"):
        ml_pipeline = Databricks("Vector Embedding\n& FAISS Index")

    # Azure Cloud
    with Cluster("Azure Services"):
        storage = BlobStorage("Vector\nStorage")
        function = FunctionApps("Query\nProcessor")
        
    # Client Interfaces
    with Cluster("Client Interfaces"):
        rest_api = FastAPI("REST\nAPI")
        web_interface = Client("Web\nInterface")
        extensions = Storage("Platform\nExtensions")

    # Define the flows with modern styling
    knowledge_bases >> Edge(color="#0078D4", label="Pull") >> scheduler
    documents >> Edge(color="#0078D4", label="Import") >> scheduler
    databases >> Edge(color="#0078D4", label="Extract") >> scheduler
    archives >> Edge(color="#0078D4", label="Archive") >> scheduler
    
    scheduler >> Edge(color="#0078D4", label="Trigger") >> queue
    queue >> Edge(color="#0078D4", label="Process") >> extractor
    extractor >> Edge(color="#0078D4", label="Transform") >> ml_pipeline
    ml_pipeline >> Edge(color="#0078D4", label="Store") >> storage
    
    storage << Edge(color="#0078D4", label="Load") << function
    function >> Edge(color="#0078D4", label="Response") >> [rest_api, web_interface, extensions]
    [rest_api, web_interface, extensions] >> Edge(color="#0078D4", label="Query") >> function

import os
from dotenv import load_dotenv

import datasets
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_huggingface import HuggingFaceEmbeddings
from tqdm import tqdm
from transformers import AutoTokenizer

# from langchain_openai import OpenAIEmbeddings
from smolagents import LiteLLMModel, Tool
from smolagents.agents import CodeAgent

load_dotenv()
# from smolagents.agents import ToolCallingAgent


# knowledge_base = datasets.load_dataset("m-ric/huggingface_doc", split="train")

# source_docs = [
#     Document(page_content=doc["text"], metadata={"source": doc["source"].split("/")[1]}) for doc in knowledge_base
# ]

# For your own PDFs, you can use the following code to load them into source_docs
pdf_directory = "/Users/jasper/Desktop/knowledgeBase/batch_upload"
md_files = [
    os.path.join(pdf_directory, f)
    for f in os.listdir(pdf_directory)
    if f.endswith(".md")
]
source_docs = []

for file_path in md_files:
    loader = UnstructuredMarkdownLoader(file_path)
    source_docs.extend(loader.load())

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

# Now split the loaded documents
splits = text_splitter.split_documents(source_docs)


print(f"Number of documents loaded: {len(source_docs)}")
if source_docs:
    print(f"First document content (first 200 chars): {source_docs[0].page_content[:200]}")
print(f"Number of chunks: {len(splits)}")
if splits:
    print(f"First chunk content (first 200 chars): {splits[0].page_content[:200]}")

# 3. Create embeddings and store in ChromaDB
model_name = "sentence-transformers/all-MiniLM-L6-v2"
# model_name = "sentence-transformers/all-mpnet-base-v2"
# model_name = "BAAI/bge-small-en-v1.5"
# model_name = "infgrad/stella-base-en-v2"
embeddings = HuggingFaceEmbeddings(model_name=model_name)

# Create and persist the vector store
vector_store = Chroma.from_documents(splits, embeddings, persist_directory="./chroma_db_bazi")


class RetrieverTool(Tool):
    name = "retriever"
    description = (
        "Uses semantic search to retrieve the parts of documentation that could be most relevant to answer your query."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to perform. This should be semantically close to your target documents. Use the affirmative form rather than a question.",
        }
    }
    output_type = "string"

    def __init__(self, vector_store, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = vector_store

    def forward(self, query: str) -> str:
        assert isinstance(query, str), "Your search query must be a string"
        docs = self.vector_store.similarity_search(query, k=3)
        return "\nRetrieved documents:\n" + "".join(
            [f"\n\n===== Document {str(i)} =====\n" + doc.page_content for i, doc in enumerate(docs)]
        )


retriever_tool = RetrieverTool(vector_store)

# Choose which LLM engine to use!

# from smolagents import InferenceClientModel
# model = InferenceClientModel(model_id="meta-llama/Llama-3.3-70B-Instruct")

# from smolagents import TransformersModel
# model = TransformersModel(model_id="meta-llama/Llama-3.2-2B-Instruct")

# For anthropic: change model_id below to 'anthropic/claude-3-5-sonnet-20240620' and also change 'os.environ.get("ANTHROPIC_API_KEY")'
model = LiteLLMModel(
    model_id="gpt-4o-mini",
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# # You can also use the ToolCallingAgent class
# agent = ToolCallingAgent(
#     tools=[retriever_tool],
#     model=model,
#     verbose=True,
# )

agent = CodeAgent(
    tools=[retriever_tool],
    model=model,
    max_steps=4,
    verbosity_level=2,
)

agent_output = agent.run("偏印格代表着什么？")


print("Final output:")
print(agent_output)

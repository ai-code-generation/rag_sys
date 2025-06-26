# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import yaml
from typing import Any, Dict, Generator, List

from langchain_community.document_loaders import UnstructuredFileLoader, TextLoader
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_text_splitters import Language
from langchain_core.documents import Document
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain.retrievers import ContextualCompressionRetriever

from chain_server.base import BaseExample
from chain_server.tracing import langchain_instrumentation_class_wrapper
from chain_server.utils import (
    create_vectorstore_langchain,
    del_docs_vectorstore_langchain,
    get_config,
    get_docs_vectorstore_langchain,
    get_embedding_model,
    get_llm,
    get_prompts,
    get_ranking_model,
    get_text_splitter,
    get_vectorstore,
)

logger = logging.getLogger(__name__)
vector_store_path = "vectorstore.pkl"
document_embedder = get_embedding_model()
text_splitter = None
settings = get_config()
prompts = get_prompts()

try:
    vectorstore = create_vectorstore_langchain(document_embedder=document_embedder)
except Exception as e:
    vectorstore = None
    logger.info(f"Unable to connect to vector store during initialization: {e}")


def load_yaml_structured(file_path: str) -> List[Document]:
    """
    Load YAML file with structured parsing to better handle hierarchical data.
    Handles both single documents and multi-entry YAML files.

    Args:
        file_path (str): Path to the YAML file

    Returns:
        List[Document]: List of documents with structured content
    """
    try:
        # First, try to load as multiple documents
        documents = []
        with open(file_path, 'r', encoding='utf-8') as file:
            yaml_docs = list(yaml.safe_load_all(file))

        # If we only get one document, check if it's a multi-entry file
        if len(yaml_docs) == 1 and yaml_docs[0] is not None:
            yaml_content = yaml_docs[0]

            # Check if this might be a multi-entry file that wasn't properly separated
            with open(file_path, 'r', encoding='utf-8') as file:
                raw_content = file.read()

            # Look for multiple id: entries which suggests multiple logical documents
            import re
            id_matches = re.findall(r'^id:\s*(\w+)', raw_content, re.MULTILINE)

            if len(id_matches) > 1:
                # This is a multi-entry file, split it manually
                documents = _split_multi_entry_yaml(raw_content)
            else:
                # Single document
                documents = [yaml_content]
        else:
            # Multiple documents properly separated
            documents = [doc for doc in yaml_docs if doc is not None]

        # Process each document
        result_documents = []
        for i, yaml_content in enumerate(documents):
            if yaml_content is None:
                continue

            # Convert YAML content to structured text representation
            if isinstance(yaml_content, dict):
                structured_content = _format_yaml_dict(yaml_content)
            elif isinstance(yaml_content, list):
                structured_content = _format_yaml_list(yaml_content)
            else:
                structured_content = str(yaml_content)

            # Create document with enhanced metadata
            metadata = {
                "source": file_path,
                "file_type": "yaml",
                "yaml_structure": type(yaml_content).__name__,
                "has_nested_structure": _has_nested_structure(yaml_content),
                "document_index": i
            }

            # Add document-specific metadata
            if isinstance(yaml_content, dict):
                if 'id' in yaml_content:
                    metadata["document_id"] = yaml_content['id']
                if 'title' in yaml_content:
                    metadata["document_title"] = yaml_content['title']

            # Extract semantic metadata from YAML content
            semantic_metadata = _extract_semantic_metadata(yaml_content, file_path)
            metadata.update(semantic_metadata)

            result_documents.append(Document(page_content=structured_content, metadata=metadata))

        return result_documents if result_documents else [Document(page_content="Empty YAML file", metadata={"source": file_path, "file_type": "yaml"})]

    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML file {file_path}: {e}. Falling back to TextLoader.")
        # Fallback to TextLoader if YAML parsing fails
        return TextLoader(file_path, encoding='utf-8').load()
    except Exception as e:
        logger.error(f"Error loading YAML file {file_path}: {e}")
        raise


def _format_yaml_dict(data: dict, indent: int = 0) -> str:
    """Format dictionary data into a structured text representation preserving full content."""
    lines = []
    prefix = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_format_yaml_dict(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            lines.append(_format_yaml_list(value, indent + 1))
        else:
            # Preserve multiline strings and complex values
            if isinstance(value, str) and ('\n' in value or len(value) > 100):
                # Handle multiline strings properly
                lines.append(f"{prefix}{key}: |")
                for line in str(value).split('\n'):
                    lines.append(f"{prefix}  {line}")
            else:
                lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines)


def _format_yaml_list(data: list, indent: int = 0) -> str:
    """Format list data into a structured text representation preserving full content."""
    lines = []
    prefix = "  " * indent

    for i, item in enumerate(data):
        if isinstance(item, dict):
            # Don't use generic "Item X" labels - preserve the actual structure
            lines.append(f"{prefix}-")
            # Format each key-value pair in the dictionary
            for key, value in item.items():
                if isinstance(value, dict):
                    lines.append(f"{prefix}  {key}:")
                    lines.append(_format_yaml_dict(value, indent + 2))
                elif isinstance(value, list):
                    lines.append(f"{prefix}  {key}:")
                    lines.append(_format_yaml_list(value, indent + 2))
                else:
                    # Handle multiline strings properly
                    if isinstance(value, str) and ('\n' in value or len(value) > 100):
                        lines.append(f"{prefix}  {key}: |")
                        for line in str(value).split('\n'):
                            lines.append(f"{prefix}    {line}")
                    else:
                        lines.append(f"{prefix}  {key}: {value}")
        elif isinstance(item, list):
            lines.append(f"{prefix}- ")
            lines.append(_format_yaml_list(item, indent + 1))
        else:
            lines.append(f"{prefix}- {item}")

    return "\n".join(lines)


def _has_nested_structure(data: Any) -> bool:
    """Check if YAML data has nested structures (dicts or lists)."""
    if isinstance(data, dict):
        return any(isinstance(v, (dict, list)) for v in data.values())
    elif isinstance(data, list):
        return any(isinstance(item, (dict, list)) for item in data)
    return False


def _split_multi_entry_yaml(raw_content: str) -> List[Any]:
    """
    Split a multi-entry YAML file into separate documents.
    Handles files with multiple entries that share the same top-level keys.

    Args:
        raw_content (str): Raw YAML file content

    Returns:
        List[Any]: List of parsed YAML documents
    """
    import re

    # Find all id: entries to identify document boundaries
    id_pattern = r'^id:\s*(\w+)'
    matches = list(re.finditer(id_pattern, raw_content, re.MULTILINE))

    if len(matches) <= 1:
        # Single document, parse normally
        return [yaml.safe_load(raw_content)]

    documents = []

    for i, match in enumerate(matches):
        start_pos = match.start()

        # Find the end position (start of next document or end of file)
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
            # Look for the last non-empty line before the next document
            content_before_next = raw_content[start_pos:end_pos].rstrip()
            # Find the actual end by looking for the last meaningful content
            lines = content_before_next.split('\n')
            while lines and (not lines[-1].strip() or lines[-1].strip().startswith('#')):
                lines.pop()
            if lines:
                content_before_next = '\n'.join(lines)
            document_content = content_before_next
        else:
            # Last document, take everything to the end
            document_content = raw_content[start_pos:].rstrip()

        try:
            # Parse this document section
            parsed_doc = yaml.safe_load(document_content)
            if parsed_doc is not None:
                documents.append(parsed_doc)
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML document section starting with {match.group()}: {e}")
            continue

    return documents


def _extract_semantic_metadata(yaml_content: Any, file_path: str) -> Dict[str, Any]:
    """
    Extract semantic metadata from YAML content for enhanced RAG retrieval.
    Uses generic patterns to work with various YAML file types.

    Args:
        yaml_content: Parsed YAML content
        file_path: Path to the YAML file

    Returns:
        Dict containing semantic metadata
    """
    metadata = {}

    try:
        # Basic structure analysis
        if isinstance(yaml_content, list):
            metadata["yaml_items_count"] = len(yaml_content)
            metadata["yaml_type"] = "array"
        elif isinstance(yaml_content, dict):
            metadata["yaml_type"] = "object"
            metadata["top_level_keys"] = list(yaml_content.keys())[:10]  # Limit to first 10 keys
        else:
            metadata["yaml_type"] = "scalar"

        # Generic key-value extraction
        all_keys = set()
        all_values = []

        def extract_from_structure(data, depth=0):
            """Recursively extract keys and values from nested structures."""
            if depth > 5:  # Prevent infinite recursion
                return

            if isinstance(data, dict):
                all_keys.update(data.keys())
                for key, value in data.items():
                    if isinstance(value, str) and len(value) < 100:  # Reasonable string values
                        all_values.append(value)
                    elif isinstance(value, (dict, list)):
                        extract_from_structure(value, depth + 1)
                    elif isinstance(value, (int, float, bool)):
                        all_values.append(str(value))

            elif isinstance(data, list):
                for item in data:
                    extract_from_structure(item, depth + 1)

        extract_from_structure(yaml_content)

        # Categorize common key patterns
        key_categories = _categorize_keys(all_keys)
        if key_categories:
            metadata["key_categories"] = key_categories

        # Extract common metadata patterns
        common_metadata = _extract_common_patterns(yaml_content)
        metadata.update(common_metadata)

        # Analyze content themes
        content_themes = _analyze_content_themes(file_path, all_values)
        if content_themes:
            metadata["content_themes"] = content_themes

        # Add structural complexity
        metadata["structural_complexity"] = _assess_structural_complexity(yaml_content)

        # Add file-based metadata
        filename = os.path.basename(file_path)
        metadata["filename"] = filename
        metadata["file_category"] = _categorize_filename(filename)

    except Exception as e:
        logger.warning(f"Failed to extract semantic metadata from {file_path}: {e}")

    return metadata


def _categorize_keys(keys: set) -> Dict[str, List[str]]:
    """Categorize YAML keys into common patterns."""
    categories = {
        "configuration": [],
        "metadata": [],
        "workflow": [],
        "data": [],
        "api": [],
        "deployment": [],
        "other": []
    }

    # Define key patterns for different categories
    patterns = {
        "configuration": ["config", "settings", "options", "parameters", "env", "environment"],
        "metadata": ["id", "name", "title", "description", "version", "author", "created", "modified"],
        "workflow": ["steps", "tasks", "jobs", "pipeline", "stage", "action", "workflow"],
        "data": ["data", "items", "records", "entries", "list", "array", "table"],
        "api": ["endpoint", "url", "method", "headers", "response", "request", "api"],
        "deployment": ["deploy", "build", "docker", "kubernetes", "service", "port", "host"]
    }

    for key in keys:
        key_lower = str(key).lower()
        categorized = False

        for category, pattern_list in patterns.items():
            if any(pattern in key_lower for pattern in pattern_list):
                categories[category].append(str(key))
                categorized = True
                break

        if not categorized:
            categories["other"].append(str(key))

    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def _extract_common_patterns(yaml_content: Any) -> Dict[str, Any]:
    """Extract common metadata patterns from YAML content."""
    metadata = {}

    def search_in_structure(data, path=""):
        """Search for common patterns in nested structures."""
        if isinstance(data, dict):
            # Look for common metadata fields
            for key, value in data.items():
                key_lower = str(key).lower()

                # Version information
                if key_lower in ["version", "ver", "v"]:
                    metadata.setdefault("versions", []).append(str(value))

                # Environment information
                elif key_lower in ["environment", "env", "stage"]:
                    metadata.setdefault("environments", []).append(str(value))

                # Service/application names
                elif key_lower in ["name", "service", "app", "application"]:
                    metadata.setdefault("services", []).append(str(value))

                # Tags or labels
                elif key_lower in ["tags", "labels", "categories"]:
                    if isinstance(value, list):
                        metadata.setdefault("tags", []).extend([str(v) for v in value])
                    else:
                        metadata.setdefault("tags", []).append(str(value))

                # Ports
                elif key_lower in ["port", "ports"] and isinstance(value, (int, str)):
                    metadata.setdefault("ports", []).append(str(value))

                # Recursively search nested structures
                if isinstance(value, (dict, list)):
                    search_in_structure(value, f"{path}.{key}" if path else key)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                search_in_structure(item, f"{path}[{i}]" if path else f"[{i}]")

    search_in_structure(yaml_content)

    # Deduplicate and limit lists
    for key in metadata:
        if isinstance(metadata[key], list):
            metadata[key] = list(set(metadata[key]))[:10]  # Limit to 10 items

    return metadata


def _analyze_content_themes(file_path: str, values: List[str]) -> List[str]:
    """Analyze content to identify themes and technologies."""
    themes = set()

    # Combine file content analysis
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().lower()

        # General technology patterns
        tech_patterns = {
            "docker": ["docker", "dockerfile", "container"],
            "kubernetes": ["kubernetes", "k8s", "kubectl", "pod", "deployment"],
            "database": ["database", "db", "sql", "mysql", "postgres", "mongodb"],
            "web": ["http", "https", "api", "rest", "web", "server"],
            "cloud": ["aws", "azure", "gcp", "cloud", "s3", "ec2"],
            "ci_cd": ["ci", "cd", "pipeline", "build", "deploy", "jenkins", "github"],
            "monitoring": ["monitor", "log", "metric", "alert", "prometheus"],
            "security": ["auth", "token", "ssl", "tls", "certificate", "security"]
        }

        for theme, keywords in tech_patterns.items():
            if any(keyword in content for keyword in keywords):
                themes.add(theme)

    except Exception:
        pass

    # Analyze values for additional themes
    value_text = " ".join(values).lower()
    for theme, keywords in tech_patterns.items():
        if any(keyword in value_text for keyword in keywords):
            themes.add(theme)

    return sorted(list(themes))


def _assess_structural_complexity(data: Any, depth: int = 0) -> str:
    """Assess the structural complexity of YAML content."""
    if depth > 6:
        return "very_high"

    complexity_score = 0

    if isinstance(data, dict):
        complexity_score += len(data)
        for value in data.values():
            if isinstance(value, (dict, list)):
                child_complexity = _assess_structural_complexity(value, depth + 1)
                complexity_score += {"low": 1, "medium": 2, "high": 3, "very_high": 4}.get(child_complexity, 0)

    elif isinstance(data, list):
        complexity_score += len(data)
        for item in data:
            if isinstance(item, (dict, list)):
                child_complexity = _assess_structural_complexity(item, depth + 1)
                complexity_score += {"low": 1, "medium": 2, "high": 3, "very_high": 4}.get(child_complexity, 0)

    if complexity_score > 50:
        return "very_high"
    elif complexity_score > 20:
        return "high"
    elif complexity_score > 5:
        return "medium"
    else:
        return "low"


def _categorize_filename(filename: str) -> str:
    """Categorize file based on filename patterns."""
    filename_lower = filename.lower()

    if any(word in filename_lower for word in ["config", "configuration", "settings"]):
        return "configuration"
    elif any(word in filename_lower for word in ["docker", "compose"]):
        return "deployment"
    elif any(word in filename_lower for word in ["test", "spec"]):
        return "testing"
    elif any(word in filename_lower for word in ["data", "schema", "model"]):
        return "data"
    elif any(word in filename_lower for word in ["workflow", "pipeline", "ci", "cd"]):
        return "workflow"
    else:
        return "general"


def _print_llm_prompt(chain_type: str, formatted_prompt: str, query: str, context: str = None) -> None:
    """
    Print the complete prompt that will be sent to the LLM in a structured format.

    Args:
        chain_type (str): Type of chain (e.g., "RAG Chain", "LLM Chain")
        formatted_prompt (str): The complete formatted prompt
        query (str): The user's original query
        context (str, optional): Retrieved context for RAG chains
    """
    print("\n" + "="*80)
    print(f"🤖 LLM PROMPT - {chain_type}")
    print("="*80)

    print(f"\n📝 USER QUERY:")
    print(f"   {query}")

    if context:
        print(f"\n📚 RETRIEVED CONTEXT:")
        print(f"   Length: {len(context)} characters")
        print(f"   Preview: {context[:200]}{'...' if len(context) > 200 else ''}")

    print(f"\n🎯 COMPLETE PROMPT SENT TO LLM:")
    print("-" * 60)
    print(formatted_prompt)
    print("-" * 60)

    print(f"\n📊 PROMPT STATISTICS:")
    print(f"   Total length: {len(formatted_prompt)} characters")
    print(f"   Word count: {len(formatted_prompt.split())} words")
    print(f"   Line count: {formatted_prompt.count(chr(10)) + 1} lines")

    # Log to logger as well for persistence
    logger.info(f"[{chain_type}] Prompt sent to LLM: {formatted_prompt}")

    print("="*80 + "\n")


@langchain_instrumentation_class_wrapper
class NvidiaAPICatalog(BaseExample):
    def ingest_docs(self, filepath: str, filename: str) -> None:
        """Ingests documents to the VectorDB.
        It's called when the POST endpoint of `/documents` API is invoked.

        Args:
            filepath (str): The path to the document file.
            filename (str): The name of the document file.

        Raises:
            ValueError: If there's an error during document ingestion or the file format is not supported.
        """
        # Make file extension validation case-insensitive
        filename_lower = filename.lower()
        if not filename_lower.endswith((".txt", ".pdf", ".md", ".java", ".yaml", ".yml")):
            raise ValueError(f"{filename} is not a valid Text, PDF, Markdown, Java, or YAML file")
        try:
            # Load raw documents from the directory
            _path = filepath

            # Use specialized loaders based on file type
            if filename_lower.endswith(".java"):
                # Use LanguageParser for Java source code files
                loader = GenericLoader.from_filesystem(
                    path=os.path.dirname(_path),
                    glob=os.path.basename(_path),
                    parser=LanguageParser(language=Language.JAVA)
                )
                raw_documents = loader.load()
            elif filename_lower.endswith((".yaml", ".yml")):
                # Use structured YAML loader for better parsing of hierarchical data
                # Alternative: You can also use UnstructuredFileLoader for simpler approach
                # raw_documents = UnstructuredFileLoader(_path).load()
                raw_documents = load_yaml_structured(_path)
            else:
                # Use UnstructuredFileLoader for other file types (PDF, TXT, MD)
                raw_documents = UnstructuredFileLoader(_path).load()

            if raw_documents:
                global text_splitter
                # Get text splitter instance, it is selected based on environment variable APP_TEXTSPLITTER_MODELNAME
                # tokenizer dimension of text splitter should be same as embedding model
                if not text_splitter:
                    text_splitter = get_text_splitter()

                # split documents based on configuration provided
                documents = text_splitter.split_documents(raw_documents)
                vs = get_vectorstore(vectorstore, document_embedder)
                # ingest documents into vectorstore
                vs.add_documents(documents)
            else:
                logger.warning("No documents available to process!")
        except Exception as e:
            logger.error(f"Failed to ingest document due to exception {e}")
            raise ValueError("Failed to upload document. Please upload an unstructured text document.")

    def llm_chain(self, query: str, chat_history: List["Message"], **kwargs) -> Generator[str, None, None]:
        """Execute a simple LLM chain using the components defined above.
        It's called when the `/generate` API is invoked with `use_knowledge_base` set to `False`.

        Args:
            query (str): Query to be answered by llm.
            chat_history (List[Message]): Conversation history between user and chain.
        """

        logger.info("Using llm to generate response directly without knowledge base.")
        # WAR: Disable chat history (UI consistency).
        chat_history = []
        system_message = [("system", prompts.get("chat_template", ""))]
        conversation_history = [(msg.role, msg.content) for msg in chat_history]
        user_input = [("user", "{input}")]

        # Checking if conversation_history is not None and not empty
        prompt_template = (
            ChatPromptTemplate.from_messages(system_message + conversation_history + user_input)
            if conversation_history
            else ChatPromptTemplate.from_messages(system_message + user_input)
        )

        llm = get_llm(**kwargs)

        # Simple langchain chain to generate response based on user's query
        chain = prompt_template | llm | StrOutputParser()
        augmented_user_input = "\n\nQuestion: " + query + "\n"

        # Format and print the complete prompt before sending to LLM
        formatted_prompt = prompt_template.format(input=augmented_user_input)
        _print_llm_prompt("LLM Chain (No Knowledge Base)", formatted_prompt, query)

        return chain.stream({"input": augmented_user_input}, config={"callbacks": [self.cb_handler]})

    def rag_chain(self, query: str, chat_history: List["Message"], **kwargs) -> Generator[str, None, None]:
        """Execute a Retrieval Augmented Generation chain using the components defined above.
        It's called when the `/generate` API is invoked with `use_knowledge_base` set to `True`.

        Args:
            query (str): Query to be answered by llm.
            chat_history (List[Message]): Conversation history between user and chain.
        """

        logger.info("Using rag to generate response from document")
        # WAR: Disable chat history (UI consistency).
        chat_history = []

        # Use the base RAG template for system message
        base_system_prompt = prompts.get("rag_template", "")
        if "S32DSGEN" in query:
            logger.info("S32DSGEN keyword detected, will add specialized prompt to user input")

        system_message = [("system", base_system_prompt)]

        conversation_history = [(msg.role, msg.content) for msg in chat_history]
        user_input = [("user", "{input}")]

        # Checking if conversation_history is not None and not empty
        prompt_template = (
            ChatPromptTemplate.from_messages(system_message + conversation_history + user_input)
            if conversation_history
            else ChatPromptTemplate.from_messages(system_message + user_input)
        )

        llm = get_llm(**kwargs)

        # Create a simple chain with conversation history and context
        chain = prompt_template | llm | StrOutputParser()

        try:
            vs = get_vectorstore(vectorstore, document_embedder)
            if vs != None:
                try:
                    logger.info(
                        f"Getting retrieved top k values: {settings.retriever.top_k} with confidence threshold: {settings.retriever.score_threshold}"
                    )
                    base_retriever = vs.as_retriever(
                        search_type="similarity_score_threshold",
                        search_kwargs={
                            "score_threshold": settings.retriever.score_threshold,
                            "k": settings.retriever.top_k,
                        },
                    )

                    # Get more documents for reranking
                    retriever_for_rerank = vs.as_retriever(
                        search_type="similarity_score_threshold",
                        search_kwargs={
                            "score_threshold": settings.retriever.score_threshold,
                            "k": settings.retriever.top_k * 2,  # Get more docs for reranking
                        },
                    )
                    initial_docs = retriever_for_rerank.get_relevant_documents(query, callbacks=[self.cb_handler])

                    # Try to get ranking model for reranking
                    ranking_model = get_ranking_model()
                    if ranking_model and len(initial_docs) > 0:
                        logger.info(f"Using ranking model for reranking {len(initial_docs)} retrieved documents")
                        try:
                            # Prepare documents for reranking
                            doc_texts = [doc.page_content for doc in initial_docs]

                            # Use the ranking model to rerank documents
                            reranked_docs = ranking_model.compress_documents(initial_docs, query)
                            docs = reranked_docs[:settings.retriever.top_k]  # Take top k after reranking
                            logger.info(f"Successfully reranked documents, using top {len(docs)} results")
                        except Exception as e:
                            logger.error(f"Failed to rerank documents: {e}")
                            logger.info("Falling back to original retrieval results")
                            docs = initial_docs[:settings.retriever.top_k]
                    else:
                        logger.info("No ranking model available or no documents to rerank, using base retrieval")
                        docs = initial_docs[:settings.retriever.top_k]
                except NotImplementedError:
                    # Some retriever like milvus don't have similarity score threshold implemented
                    base_retriever = vs.as_retriever()

                    # Get more documents for reranking
                    retriever_for_rerank = vs.as_retriever()
                    initial_docs = retriever_for_rerank.get_relevant_documents(query, callbacks=[self.cb_handler])

                    # Try to get ranking model for reranking
                    ranking_model = get_ranking_model()
                    if ranking_model and len(initial_docs) > 0:
                        logger.info(f"Using ranking model for reranking {len(initial_docs)} retrieved documents")
                        try:
                            # Use the ranking model to rerank documents
                            reranked_docs = ranking_model.compress_documents(initial_docs, query)
                            docs = reranked_docs[:settings.retriever.top_k]  # Take top k after reranking
                            logger.info(f"Successfully reranked documents, using top {len(docs)} results")
                        except Exception as e:
                            logger.error(f"Failed to rerank documents: {e}")
                            logger.info("Falling back to original retrieval results")
                            docs = initial_docs[:settings.retriever.top_k]
                    else:
                        logger.info("No ranking model available or no documents to rerank, using base retrieval")
                        docs = initial_docs[:settings.retriever.top_k]

                logger.debug(f"Retrieved documents are: {docs}")
                if not docs:
                    logger.warning("Retrieval failed to get any relevant context")
                    return iter(
                        ["No response generated from LLM, make sure your query is relavent to the ingested document."]
                    )

                context = ""
                for doc in docs:
                    context += doc.page_content + "\n\n"

                # Create input with context and user query to be ingested in prompt to retrieve contextal response from llm
                augmented_user_input = "Context: " + context + "\n\nQuestion: " + query + "\n"

                # Add S32 specialized prompt to user input if keyword is detected
                if "S32DSGEN" in query:
                    s32_user_prompt = """
You are an expert test automation assistant specializing in the NXP S32 Design Studio (S32DS) IDE.
You are an intelligent assistant using s32ds libary.
If the debugger is not supported, generate a TODO comment.
Your task is to generate **only the code** that automates a user's request or test step using the appropriate function calls or Java method stubs.

🧠 Rules:
1. Always return **only code**, wrapped in a proper code block (use ``` syntax).
2. The code must reflect the **intended action** described in the user query.
4. For workflows, generate methods in format:
   ```java
   public void stepXX() {
       // code
   }
   ```
5. No extra explanation. Code only.

"""
                    augmented_user_input = augmented_user_input + s32_user_prompt

                # Format and print the complete prompt before sending to LLM
                formatted_prompt = prompt_template.format(input=augmented_user_input)
                _print_llm_prompt("RAG Chain (With Knowledge Base)", formatted_prompt, query, context)
                return chain.stream({"input": augmented_user_input}, config={"callbacks": [self.cb_handler]})
        except Exception as e:
            logger.warning(f"Failed to generate response due to exception {e}")
        logger.warning("No response generated from LLM, make sure you've ingested document.")
        return iter(
            ["No response generated from LLM, make sure you have ingested document from the Knowledge Base Tab."]
        )

    def document_search(self, content: str, num_docs: int) -> List[Dict[str, Any]]:
        """Search for the most relevant documents for the given search parameters.
        It's called when the `/search` API is invoked.

        Args:
            content (str): Query to be searched from vectorstore.
            num_docs (int): Number of similar docs to be retrieved from vectorstore.
        """

        try:
            vs = get_vectorstore(vectorstore, document_embedder)
            if vs != None:
                try:
                    base_retriever = vs.as_retriever(
                        search_type="similarity_score_threshold",
                        search_kwargs={"score_threshold": settings.retriever.score_threshold, "k": num_docs},
                    )

                    # Get more documents for reranking
                    retriever_for_rerank = vs.as_retriever(
                        search_type="similarity_score_threshold",
                        search_kwargs={"score_threshold": settings.retriever.score_threshold, "k": num_docs * 2},
                    )
                    initial_docs = retriever_for_rerank.get_relevant_documents(content, callbacks=[self.cb_handler])

                    # Try to get ranking model for reranking
                    ranking_model = get_ranking_model()
                    if ranking_model and len(initial_docs) > 0:
                        logger.info(f"Using ranking model for reranking {len(initial_docs)} search results")
                        try:
                            # Use the ranking model to rerank documents
                            reranked_docs = ranking_model.compress_documents(initial_docs, content)
                            docs = reranked_docs[:num_docs]  # Take top k after reranking
                            logger.info(f"Successfully reranked documents, using top {len(docs)} results")
                        except Exception as e:
                            logger.error(f"Failed to rerank documents: {e}")
                            logger.info("Falling back to original search results")
                            docs = initial_docs[:num_docs]
                    else:
                        logger.info("No ranking model available or no documents to rerank, using base search")
                        docs = initial_docs[:num_docs]
                except NotImplementedError:
                    # Some retriever like milvus don't have similarity score threshold implemented
                    base_retriever = vs.as_retriever()

                    # Get more documents for reranking
                    retriever_for_rerank = vs.as_retriever()
                    initial_docs = retriever_for_rerank.get_relevant_documents(content, callbacks=[self.cb_handler])

                    # Try to get ranking model for reranking
                    ranking_model = get_ranking_model()
                    if ranking_model and len(initial_docs) > 0:
                        logger.info(f"Using ranking model for reranking {len(initial_docs)} search results")
                        try:
                            # Use the ranking model to rerank documents
                            reranked_docs = ranking_model.compress_documents(initial_docs, content)
                            docs = reranked_docs[:num_docs]  # Take top k after reranking
                            logger.info(f"Successfully reranked documents, using top {len(docs)} results")
                        except Exception as e:
                            logger.error(f"Failed to rerank documents: {e}")
                            logger.info("Falling back to original search results")
                            docs = initial_docs[:num_docs]
                    else:
                        logger.info("No ranking model available or no documents to rerank, using base search")
                        docs = initial_docs[:num_docs]

                result = []
                for doc in docs:
                    result.append(
                        {"source": os.path.basename(doc.metadata.get('source', '')), "content": doc.page_content}
                    )
                return result
            return []
        except Exception as e:
            logger.error(f"Error from POST /search endpoint. Error details: {e}")

    def get_documents(self) -> List[str]:
        """Retrieves filenames stored in the vector store.
        It's called when the GET endpoint of `/documents` API is invoked.
        
        Returns:
            List[str]: List of filenames ingested in vectorstore.
        """
        try:
            vs = get_vectorstore(vectorstore, document_embedder)
            if vs:
                return get_docs_vectorstore_langchain(vs)
        except Exception as e:
            logger.error(f"Vectorstore not initialized. Error details: {e}")
        return []

    def delete_documents(self, filenames: List[str]) -> bool:
        """Delete documents from the vector index.
        It's called when the DELETE endpoint of `/documents` API is invoked.

        Args:
            filenames (List[str]): List of filenames to be deleted from vectorstore.
        """
        try:
            # Get vectorstore instance
            vs = get_vectorstore(vectorstore, document_embedder)
            if vs:
                return del_docs_vectorstore_langchain(vs, filenames)
        except Exception as e:
            logger.error(f"Vectorstore not initialized. Error details: {e}")
        return False

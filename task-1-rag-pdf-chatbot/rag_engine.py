import io
import os
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import pypdf
from pypdf.errors import PdfReadError

from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from chromadb.api.models.Collection import Collection

from rag_config import RAGConfig


class PDFExtractionError(Exception):
    pass


class ScannedPDFError(Exception):
    pass


class RAGEngine:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or RAGConfig.get_active_provider()
        self.client = chromadb.Client()
        self.active_collection: Optional[Collection] = None
        self.current_doc_hash: Optional[str] = None
        self.current_filename: Optional[str] = None
        self.doc_metadata: Dict[str, Any] = {}

    def extract_text_from_pdf(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > RAGConfig.MAX_FILE_SIZE_MB:
            raise PDFExtractionError(
                f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of {RAGConfig.MAX_FILE_SIZE_MB} MB."
            )

        if len(file_bytes) == 0:
            raise PDFExtractionError("The uploaded file is empty (0 bytes).")

        try:
            stream = io.BytesIO(file_bytes)
            reader = pypdf.PdfReader(stream)
        except PdfReadError as e:
            raise PDFExtractionError(f"Corrupt or invalid PDF file: {str(e)}")
        except Exception as e:
            raise PDFExtractionError(f"Failed to read PDF structure: {str(e)}")

        if reader.is_encrypted:
            raise PDFExtractionError(
                "The uploaded PDF is password-protected. Please upload an unprotected document."
            )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise PDFExtractionError("The uploaded PDF contains no pages.")

        pages_data = []
        total_extracted_chars = 0

        for page_idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            
            cleaned_text = " ".join(page_text.split())
            total_extracted_chars += len(cleaned_text)
            pages_data.append({
                "page": page_idx + 1,
                "text": cleaned_text
            })

        if total_extracted_chars < RAGConfig.MIN_EXTRACTABLE_CHARS:
            raise ScannedPDFError(
                "No extractable digital text found in this PDF. "
                "It appears to be a scanned image or empty pages. "
                "OCR processing would be required to read this document."
            )

        return pages_data

    def chunk_document(self, pages_data: List[Dict[str, Any]], filename: str) -> List[Dict[str, Any]]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAGConfig.CHUNK_SIZE,
            chunk_overlap=RAGConfig.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        chunks = []
        chunk_counter = 0

        for page_info in pages_data:
            page_num = page_info["page"]
            text = page_info["text"]
            if not text.strip():
                continue

            split_texts = splitter.split_text(text)
            for idx, chunk_text in enumerate(split_texts):
                chunk_counter += 1
                chunks.append({
                    "id": f"chunk_{chunk_counter}",
                    "text": chunk_text,
                    "metadata": {
                        "source": filename,
                        "page": page_num,
                        "chunk_index": idx,
                        "char_count": len(chunk_text)
                    }
                })

        return chunks

    def _get_embedding_for_text(self, text: str) -> List[float]:
        if self.provider == "gemini" and RAGConfig.GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=RAGConfig.GEMINI_API_KEY)
                res = client.models.embed_content(
                    model=RAGConfig.GEMINI_EMBEDDING_MODEL,
                    contents=text
                )
                return res.embeddings[0].values
            except Exception:
                pass

        return self._deterministic_embedding(text)

    def _deterministic_embedding(self, text: str, dim: int = 256) -> List[float]:
        import math
        import re
        tokens = re.findall(r"\b\w+\b", text.lower())
        if not tokens:
            return [0.0] * dim

        vec = [0.0] * dim
        for t in tokens:
            idx = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % dim
            vec[idx] += 1.0

        magnitude = math.sqrt(sum(x * x for x in vec))
        if magnitude > 0:
            vec = [x / magnitude for x in vec]
        return vec

    def index_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        if self.current_doc_hash == file_hash and self.active_collection is not None:
            return {
                "status": "cached",
                "filename": filename,
                "total_pages": self.doc_metadata.get("total_pages", 0),
                "total_chunks": self.doc_metadata.get("total_chunks", 0),
                "provider": self.provider
            }

        if self.active_collection is not None:
            try:
                self.client.delete_collection(self.active_collection.name)
            except Exception:
                pass
            self.active_collection = None

        pages_data = self.extract_text_from_pdf(file_bytes, filename)
        chunks = self.chunk_document(pages_data, filename)

        if not chunks:
            raise PDFExtractionError("No readable content could be extracted into chunks.")

        collection_name = f"doc_{file_hash[:16]}"
        try:
            self.client.delete_collection(collection_name)
        except Exception:
            pass
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        ids = [c["id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        embeddings = [self._get_embedding_for_text(t) for t in documents]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

        self.active_collection = collection
        self.current_doc_hash = file_hash
        self.current_filename = filename
        self.doc_metadata = {
            "total_pages": len(pages_data),
            "total_chunks": len(chunks),
            "chunks": chunks
        }

        return {
            "status": "indexed",
            "filename": filename,
            "total_pages": len(pages_data),
            "total_chunks": len(chunks),
            "provider": self.provider
        }

    def retrieve_context(self, question: str, top_k: int = RAGConfig.TOP_K) -> Tuple[List[Dict[str, Any]], bool]:
        if not self.active_collection:
            return [], False

        cleaned_q = question.strip()
        if not cleaned_q:
            return [], False

        query_vec = self._get_embedding_for_text(cleaned_q)

        results = self.active_collection.query(
            query_embeddings=[query_vec],
            n_results=min(top_k, self.active_collection.count())
        )

        relevant_chunks = []
        if not results or not results["documents"] or not results["documents"][0]:
            return [], False

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        distances = results["distances"][0] if results["distances"] else [0.0] * len(docs)

        for doc_text, meta, dist in zip(docs, metas, distances):
            if dist <= RAGConfig.RELEVANCE_DISTANCE_THRESHOLD:
                relevant_chunks.append({
                    "text": doc_text,
                    "page": meta.get("page", 1),
                    "source": meta.get("source", self.current_filename),
                    "distance": round(dist, 4),
                    "similarity": round(1.0 - dist, 4)
                })

        has_relevant = len(relevant_chunks) > 0
        return relevant_chunks, has_relevant

    def generate_answer(self, question: str, top_k: int = RAGConfig.TOP_K) -> Dict[str, Any]:
        cleaned_question = question.strip()
        if not cleaned_question:
            return {
                "answer": "Please enter a valid question.",
                "sources": [],
                "relevant_found": False
            }

        if not self.active_collection:
            return {
                "answer": "No document is currently indexed. Please upload a PDF first.",
                "sources": [],
                "relevant_found": False
            }

        chunks, has_relevant = self.retrieve_context(cleaned_question, top_k=top_k)

        if not has_relevant or not chunks:
            return {
                "answer": "I couldn't find this information in the uploaded document.",
                "sources": [],
                "relevant_found": False
            }

        context_parts = []
        sources = []
        for c in chunks:
            context_parts.append(f"[Page {c['page']}]: {c['text']}")
            sources.append({
                "page": c["page"],
                "similarity": c["similarity"],
                "snippet": c["text"][:180] + ("..." if len(c["text"]) > 180 else "")
            })

        context_str = "\n\n".join(context_parts)

        prompt = (
            "You are a factual document-answering assistant.\n"
            "Answer the question using only the document context provided below.\n"
            "Rules:\n"
            "1. Answer based solely on the facts directly stated in the context.\n"
            "2. If the context does not contain the answer, respond exactly with:\n"
            "   'I couldn't find this information in the uploaded document.'\n"
            "3. Mention the source page number(s) where you found the answer.\n\n"
            f"--- DOCUMENT CONTEXT ---\n{context_str}\n\n"
            f"--- QUESTION ---\n{cleaned_question}\n\n"
            "--- ANSWER ---"
        )

        answer_text = self._call_llm(prompt, question=cleaned_question, chunks=chunks)

        return {
            "answer": answer_text,
            "sources": sources,
            "relevant_found": True
        }

    def _call_llm(self, prompt: str, question: str, chunks: List[Dict[str, Any]]) -> str:
        if self.provider == "gemini" and RAGConfig.GEMINI_API_KEY:
            from google import genai
            client = genai.Client(api_key=RAGConfig.GEMINI_API_KEY)
            models = [RAGConfig.GEMINI_MODEL, RAGConfig.GEMINI_FALLBACK_MODEL]

            for model_name in models:
                for attempt in range(2):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        return response.text.strip()
                    except Exception as e:
                        err_msg = str(e).lower()
                        if "429" in err_msg or "quota" in err_msg:
                            time.sleep(1 + attempt)
                            continue
                        if "503" in err_msg or "unavailable" in err_msg or "demand" in err_msg:
                            break
                        if attempt == 1:
                            break

            return "Gemini API unavailable. Please retry in a moment."

        top_chunk = chunks[0]
        return (
            f"Based on page {top_chunk['page']}: "
            f"\"{top_chunk['text'][:250]}...\""
        )

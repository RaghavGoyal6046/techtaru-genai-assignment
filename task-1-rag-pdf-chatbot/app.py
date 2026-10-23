"""
Streamlit Web Application for Task 1: Basic RAG Pipeline.
Features:
- PDF upload & immediate validation (empty, corrupt, scanned-only detection)
- Real-time indexing into ChromaDB vector store
- Context-grounded chat with source page citations
- Anti-hallucination guardrail with relevance threshold
- Google Gemini LLM & Embeddings with Offline Mock mode
"""

import os
import sys
from pathlib import Path
import streamlit as st

# Ensure local modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rag_config import RAGConfig
from rag_engine import RAGEngine, PDFExtractionError, ScannedPDFError
from vector_math import compare_search_metrics

# Page configuration
st.set_page_config(
    page_title="TechTaru RAG Pipeline - Chat With PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, professional styling
st.markdown("""
<style>
    /* Global styles */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    
    /* Header badge */
    .custom-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .badge-primary {
        background: linear-gradient(135deg, #2563eb, #3b82f6);
        color: white;
    }
    .badge-success {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white;
    }
    .badge-warning {
        background: linear-gradient(135deg, #d97706, #f59e0b);
        color: white;
    }

    /* Cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .metric-title {
        color: #8b949e;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        color: #58a6ff;
        font-size: 1.4rem;
        font-weight: 700;
        margin-top: 4px;
    }

    /* Source citation box */
    .citation-box {
        background-color: #1f242c;
        border-left: 3px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin-top: 8px;
        font-size: 0.88rem;
    }

    /* Fallback warning box */
    .fallback-box {
        background-color: rgba(239, 68, 68, 0.1);
        border-left: 3px solid #ef4444;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin-top: 8px;
        color: #fca5a5;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "indexed_doc_name" not in st.session_state:
    st.session_state.indexed_doc_name = None

if "doc_stats" not in st.session_state:
    st.session_state.doc_stats = {}


# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("RAG Controls")
    st.caption("Document Q&A Assistant")

    st.markdown("---")
    st.subheader("1. LLM Provider")
    
    provider_options = ["gemini", "mock"]
    current_default = RAGConfig.get_active_provider()
    selected_provider = st.selectbox(
        "Active Engine",
        options=provider_options,
        index=provider_options.index(current_default) if current_default in provider_options else 0,
        help="Select Google Gemini (free API) or Offline Mock mode"
    )

    if selected_provider != st.session_state.rag_engine.provider:
        st.session_state.rag_engine = RAGEngine(provider=selected_provider)
        st.session_state.indexed_doc_name = None
        st.session_state.chat_history = []
        st.rerun()

    # Provider status indicator
    if selected_provider == "gemini":
        has_key = bool(RAGConfig.GEMINI_API_KEY)
        if has_key:
            st.success("Gemini API Connected (Free Tier)")
        else:
            st.warning("GEMINI_API_KEY not found in .env. Running in Mock Fallback.")
    else:
        st.info("Offline Mock Mode Active (Zero API key required)")

    st.markdown("---")
    st.subheader("2. Document Upload")

    uploaded_file = st.file_uploader(
        "Upload PDF Document",
        type=["pdf"],
        help="Max file size 25MB. Only digital text PDFs supported."
    )

    # Quick demo document loader button
    sample_pdf_path = Path(__file__).resolve().parent / "sample_docs" / "sample_company_policy.pdf"
    if sample_pdf_path.exists():
        if st.button("Load Prebuilt Sample PDF", use_container_width=True):
            with open(sample_pdf_path, "rb") as f:
                sample_bytes = f.read()
            with st.spinner("Indexing TechTaru Sample Policy..."):
                try:
                    result = st.session_state.rag_engine.index_pdf(sample_bytes, "sample_company_policy.pdf")
                    st.session_state.indexed_doc_name = "sample_company_policy.pdf"
                    st.session_state.doc_stats = result
                    st.session_state.chat_history = []
                    st.success("Sample document indexed successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to index sample document: {e}")

    # Process uploaded file
    if uploaded_file is not None and uploaded_file.name != st.session_state.indexed_doc_name:
        with st.spinner(f"Parsing & vectorizing {uploaded_file.name}..."):
            file_bytes = uploaded_file.read()
            try:
                result = st.session_state.rag_engine.index_pdf(file_bytes, uploaded_file.name)
                st.session_state.indexed_doc_name = uploaded_file.name
                st.session_state.doc_stats = result
                st.session_state.chat_history = []  # Clear previous chat on new document
                st.success("Document indexed cleanly in ChromaDB!")
                st.rerun()
            except PDFExtractionError as e:
                st.error(f"PDF Error: {str(e)}")
            except ScannedPDFError as e:
                st.warning(f"Unreadable Document: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected Error: {str(e)}")

    # Show Document Metrics
    if st.session_state.indexed_doc_name:
        st.markdown("---")
        st.subheader("Active Document")
        st.markdown(f"**File:** `{st.session_state.indexed_doc_name}`")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Pages</div>
                <div class="metric-value">{st.session_state.doc_stats.get('total_pages', 0)}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Chunks</div>
                <div class="metric-value">{st.session_state.doc_stats.get('total_chunks', 0)}</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("Reset Document & Clear Chat", use_container_width=True):
            st.session_state.rag_engine = RAGEngine(provider=selected_provider)
            st.session_state.indexed_doc_name = None
            st.session_state.chat_history = []
            st.session_state.doc_stats = {}
            st.rerun()


# Main Application Interface
main_tab, math_tab = st.tabs(["💬 Chat with PDF", "📐 Vector Search Math (Under the Hood)"])

with main_tab:
    st.title("📄 Chat With Your PDF")
    st.markdown(
        "A strictly grounded RAG pipeline powered by **LangChain**, **ChromaDB**, "
        "and **Cosine Vector Retrieval** with automated anti-hallucination guardrails."
    )

    if not st.session_state.indexed_doc_name:
        st.info("👈 Please upload a PDF file or click **'Load Prebuilt Sample PDF'** in the sidebar to begin.")
        
        st.markdown("""
        ### How This RAG Pipeline Works:
        1. **Text Extraction**: Uses `pypdf` to parse text and preserve page numbers.
        2. **Semantic Chunking**: Splits text into chunks with `chunk_size=1000` and `chunk_overlap=200` to prevent lost context.
        3. **Vector Embeddings**: Encodes chunks into high-dimensional vectors.
        4. **ChromaDB Cosine Space**: Indexes chunks in ChromaDB with `hnsw:space = cosine`.
        5. **Anti-Hallucination Guardrail**: Queries with distance thresholding. If no relevant chunks are found, it immediately responds *"I couldn't find this information in the uploaded document."* without fabricating facts.
        6. **Source Citations**: Returns exact page numbers and evidence snippets.
        """)
    else:
        # Display chat conversation
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Render source citations if available
                if msg.get("sources"):
                    with st.expander("🔍 View Retrieved Source Excerpts"):
                        for idx, src in enumerate(msg["sources"], 1):
                            st.markdown(f"**Source #{idx} (Page {src['page']})** — Similarity Score: `{src.get('similarity', 0):.2f}`")
                            st.markdown(f"> *\"{src['snippet']}\"*")

        # Chat Input
        if user_prompt := st.chat_input("Ask a question about the document..."):
            # 1. Validation for empty question
            if not user_prompt.strip():
                st.warning("Please enter a non-empty question.")
            else:
                # Add user message to history
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})
                with st.chat_message("user"):
                    st.markdown(user_prompt)

                # Generate Answer
                with st.chat_message("assistant"):
                    with st.spinner("Retrieving evidence & generating grounded response..."):
                        response = st.session_state.rag_engine.generate_answer(user_prompt)
                        
                        st.markdown(response["answer"])

                        # Render sources
                        if response.get("sources"):
                            with st.expander("🔍 View Retrieved Source Excerpts"):
                                for idx, src in enumerate(response["sources"], 1):
                                    st.markdown(f"**Source #{idx} (Page {src['page']})** — Similarity: `{src.get('similarity', 0):.2f}`")
                                    st.markdown(f"> *\"{src['snippet']}\"*")

                        # Save to history
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response["answer"],
                            "sources": response.get("sources", [])
                        })


# TAB 2: Vector Search Math
with math_tab:
    st.header("📐 Vector Search & Similarity Metrics")

    st.subheader("1. Mathematical Formulas")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Cosine Similarity")
        st.latex(r"\text{Cosine Similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|} = \frac{\sum_{i=1}^n A_i B_i}{\sqrt{\sum_{i=1}^n A_i^2} \sqrt{\sum_{i=1}^n B_i^2}}")
        st.markdown("""
        - **Measures**: The **angle** (direction) between two vectors.
        - **Range**: `[-1.0, 1.0]` (or `[0.0, 1.0]` for non-negative word embeddings).
        - **Key Feature**: **Magnitude Invariant**. A 10-word summary and a 1,000-word article on the same topic have the same direction!
        """)

    with col_b:
        st.markdown("#### Euclidean Distance (L2)")
        st.latex(r"\text{Euclidean Distance}(A, B) = \|A - B\| = \sqrt{\sum_{i=1}^n (A_i - B_i)^2}")
        st.markdown("""
        - **Measures**: The straight-line physical distance between points.
        - **Range**: `[0.0, \infty)`.
        - **Key Feature**: **Sensitive to Magnitude**. If vector $B$ has the exact same direction as $A$ but is 4x longer, Euclidean distance treats them as very far apart!
        """)

    st.markdown("---")
    st.subheader("2. Live Comparison Simulation")
    st.caption("Inspect how a Query Vector interacts with documents of different lengths and topics:")

    # Interactive sample vectors
    sim_query = [0.8, 0.6, 0.0]
    sim_candidates = [
        {
            "text": "Document 1: Short medical summary (Length = 1x, identical topic)",
            "vector": [0.75, 0.65, 0.1]
        },
        {
            "text": "Document 2: Comprehensive 50-page medical handbook (Length = 4x, exact same topic)",
            "vector": [3.2, 2.4, 0.0]
        },
        {
            "text": "Document 3: Italian pasta cooking guide (Length = 1x, completely unrelated topic)",
            "vector": [0.0, 0.1, 0.9]
        }
    ]

    metrics = compare_search_metrics(sim_query, sim_candidates)

    st.table([
        {
            "Candidate Document": m["text"],
            "Cosine Similarity (Higher = Closer)": m["cosine_similarity"],
            "Cosine Distance (1 - Cosine)": m["cosine_distance"],
            "Euclidean Distance (Lower = Closer)": m["euclidean_distance"],
            "Normalized Euclidean Dist": m["normalized_euclidean_distance"]
        }
        for m in metrics
    ])

    st.info("""
    💡 **Cosine vs Euclidean in Vector Search:**
    1. **Document 2**: Cosine Similarity is **1.0** because the directional angle is identical, even though the text is much longer.
    2. Raw Euclidean distance penalizes Document 2 simply due to larger vector magnitude.
    3. When vectors are unit-normalized (L2 norm = 1.0), Euclidean distance and Cosine similarity yield identical ranking.
    """)

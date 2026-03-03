"""LegacyLens Streamlit UI."""

import httpx
import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(
    page_title="LegacyLens",
    page_icon="🔍",
    layout="wide",
)

# Configuration
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")


def api_client():
    """Get HTTP client for API calls."""
    return httpx.Client(base_url=API_BASE_URL, timeout=60.0)


def search_code(query: str, top_k: int = 10) -> dict:
    """Call the query API endpoint.

    Args:
        query: Natural language query
        top_k: Number of results to retrieve

    Returns:
        API response as dictionary
    """
    with api_client() as client:
        response = client.post(
            "/api/v1/query",
            json={"query": query, "top_k": top_k},
        )
        response.raise_for_status()
        return response.json()


# Title
st.title("🔍 LegacyLens")
st.markdown("**RAG system for legacy Fortran scientific codebases**")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("About")
    st.markdown(
        """
        LegacyLens helps you understand legacy Fortran codebases
        through natural language queries with file/line citations.

        **Corpus:** USGS NSHMP Fortran hazard code
        """
    )

    st.header("Settings")
    top_k = st.slider("Results to show", min_value=1, max_value=20, value=10)

    # API status check
    st.header("System Status")
    try:
        with api_client() as client:
            health = client.get("/health").json()
            st.success(f"API: {health.get('status', 'unknown')}")
    except Exception as e:
        st.error(f"API: Unavailable ({str(e)[:50]})")

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Query")
    query = st.text_area(
        "Enter your question:",
        placeholder="e.g., Where is the ground motion prediction equation computed?",
        height=100,
    )

    search_button = st.button("Search", type="primary")

# Process search
if search_button and query.strip():
    with st.spinner("Searching and generating answer..."):
        try:
            result = search_code(query, top_k)
            st.session_state["last_result"] = result
        except httpx.HTTPStatusError as e:
            st.error(f"API error: {e.response.status_code} - {e.response.text[:200]}")
        except Exception as e:
            st.error(f"Search failed: {str(e)}")

elif search_button:
    st.warning("Please enter a query.")

# Display results
with col2:
    st.header("Results")

    if "last_result" in st.session_state:
        result = st.session_state["last_result"]

        # Display answer
        st.markdown("### Answer")
        st.markdown(result.get("answer", "No answer generated"))

        # Display latency
        latency = result.get("latency_ms", 0)
        st.caption(f"Response time: {latency:.0f}ms")

        # Display citations
        citations = result.get("citations", [])
        if citations:
            st.markdown("### Citations")
            for citation in citations:
                span = citation.get("span", {})
                file_path = span.get("file_path", "unknown")
                start_line = span.get("start_line", 0)
                end_line = span.get("end_line", 0)
                snippet = citation.get("snippet", "")

                with st.expander(f"📄 `{file_path}:{start_line}-{end_line}`"):
                    st.code(snippet[:500], language="fortran")

        # Display retrieved chunks
        chunks = result.get("chunks", [])
        if chunks:
            st.markdown("### Retrieved Chunks")
            st.caption(f"Showing {len(chunks)} most relevant chunks")

            for i, chunk in enumerate(chunks):
                span = chunk.get("span", {})
                file_path = span.get("file_path", "unknown")
                start_line = span.get("start_line", 0)
                end_line = span.get("end_line", 0)
                score = chunk.get("score", 0)
                name = chunk.get("name", "")
                chunk_type = chunk.get("chunk_type", "UNKNOWN")
                text = chunk.get("text", "")

                header = f"**{chunk_type}**: {name}" if name else f"**{chunk_type}**"
                with st.expander(f"{i+1}. {header} (`{file_path}:{start_line}`) - Score: {score:.3f}"):
                    st.code(text[:1500], language="fortran")

    else:
        st.info(
            """
            Enter a query on the left and click **Search** to find relevant code.

            The system will:
            1. Search for semantically similar code chunks
            2. Generate an answer with file:line citations
            3. Show the retrieved code snippets
            """
        )

# Sample queries
st.markdown("---")
st.markdown("### Sample Queries")
sample_queries = [
    "Where is hazard computed?",
    "What does the ground motion prediction equation do?",
    "How are earthquake magnitudes handled?",
    "Where is the probability calculation?",
    "What subroutines handle hazard curves?",
]

cols = st.columns(len(sample_queries))
for i, sample in enumerate(sample_queries):
    if cols[i].button(sample, key=f"sample_{i}"):
        st.session_state["query_input"] = sample
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: gray;">
        LegacyLens v0.1.0 | USGS NSHMP Fortran Corpus
    </div>
    """,
    unsafe_allow_html=True,
)

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
import os

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", API_BASE_URL)
except Exception:
    pass  # Use environment variable or default


def api_client():
    """Get HTTP client for API calls."""
    return httpx.Client(base_url=API_BASE_URL, timeout=60.0)


def search_code(query: str, top_k: int = 10) -> dict:
    """Call the query API endpoint."""
    with api_client() as client:
        response = client.post(
            "/api/v1/query",
            json={"query": query, "top_k": top_k},
        )
        response.raise_for_status()
        return response.json()


def lookup_symbol(symbol_name: str) -> dict:
    """Call the symbol lookup API endpoint."""
    with api_client() as client:
        response = client.get(f"/api/v1/symbols/{symbol_name}")
        response.raise_for_status()
        return response.json()


def get_call_sites(symbol_name: str) -> dict:
    """Get call sites for a symbol."""
    with api_client() as client:
        response = client.get(f"/api/v1/symbols/{symbol_name}/call-sites")
        response.raise_for_status()
        return response.json()


def get_impact(symbol_name: str) -> dict:
    """Get impact analysis for a symbol."""
    with api_client() as client:
        response = client.get(f"/api/v1/symbols/{symbol_name}/impact")
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

        **Features:**
        - 🔍 **Search**: Natural language code search
        - 🔧 **Symbol Lookup**: Find and understand functions/subroutines

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

# Main tabs
tab1, tab2 = st.tabs(["🔍 Search", "🔧 Symbol Lookup"])

# ==================== Tab 1: Search ====================
with tab1:
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

                    with st.expander(f"`{file_path}:{start_line}-{end_line}`"):
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

# ==================== Tab 2: Symbol Lookup ====================
with tab2:
    st.header("Symbol Lookup")

    col1, col2 = st.columns([2, 1])

    with col1:
        symbol_name = st.text_input(
            "Enter symbol name",
            placeholder="e.g., getABsub, hazSUBX, sum_haz",
        )

    with col2:
        st.write("")  # Spacing
        st.write("")
        lookup_btn = st.button("Lookup", type="primary")

    if lookup_btn and symbol_name:
        with st.spinner("Looking up symbol..."):
            try:
                # Get symbol info
                symbol = lookup_symbol(symbol_name)

                # Display symbol info
                symbol_data = symbol.get("symbol", {})
                st.markdown("### Symbol Info")

                info_col1, info_col2, info_col3 = st.columns(3)
                with info_col1:
                    st.metric("Kind", symbol_data.get("kind", "Unknown"))
                with info_col2:
                    st.metric("File", symbol_data.get("file", "N/A").split("\\")[-1])
                with info_col3:
                    lines = symbol_data.get("lines", "")
                    st.metric("Lines", lines)

                # Display explanation
                st.markdown("### Explanation")
                explanation = symbol.get("explanation", "No explanation available")
                st.info(explanation)

                # Display source code
                source_code = symbol.get("source_code", "")
                if source_code:
                    st.markdown("### Source Code")
                    st.code(source_code, language="fortran")

                # Get call sites
                try:
                    calls = get_call_sites(symbol_name)
                    call_sites = calls.get("call_sites", [])
                    call_count = calls.get("call_count", len(call_sites))

                    st.markdown(f"### Called By ({call_count} locations)")

                    if call_sites:
                        for site in call_sites[:10]:
                            caller_span = site.get("caller_span", {})
                            file_path = caller_span.get("file_path", "unknown")
                            caller_name = site.get("caller_name", "unknown")
                            snippet = site.get("snippet", "")

                            with st.expander(f"`{caller_name}` in `{file_path}`"):
                                if snippet:
                                    st.code(snippet, language="fortran")
                    else:
                        st.caption("No direct callers found in the corpus")
                except httpx.HTTPStatusError:
                    st.caption("Could not retrieve call sites")

                # Get impact analysis
                try:
                    impact = get_impact(symbol_name)

                    st.markdown("### Impact Analysis")

                    blast_radius = impact.get("estimated_blast_radius", "unknown")
                    radius_color = {
                        "low": "green",
                        "medium": "orange",
                        "high": "red",
                    }.get(blast_radius, "gray")

                    st.markdown(
                        f"**Blast Radius:** :{radius_color}[{blast_radius.upper()}]"
                    )

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        direct = impact.get("direct_callers", [])
                        st.metric("Direct Callers", len(direct))
                        if direct:
                            with st.expander("View"):
                                for caller in direct[:20]:
                                    st.markdown(f"- `{caller}`")

                    with col_b:
                        indirect = impact.get("indirect_callers", [])
                        st.metric("Indirect Callers", len(indirect))
                        if indirect:
                            with st.expander("View"):
                                for caller in indirect[:20]:
                                    st.markdown(f"- `{caller}`")

                    with col_c:
                        files = impact.get("files_affected", [])
                        st.metric("Files Affected", len(files))
                        if files:
                            with st.expander("View"):
                                for f in files[:20]:
                                    st.markdown(f"- `{f}`")

                except httpx.HTTPStatusError:
                    st.caption("Could not retrieve impact analysis")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    st.error(f"Symbol '{symbol_name}' not found in the corpus")
                else:
                    st.error(f"API error: {e.response.status_code}")
            except Exception as e:
                st.error(f"Lookup failed: {str(e)}")

    elif lookup_btn:
        st.warning("Please enter a symbol name.")

    # Sample symbols
    if not lookup_btn:
        st.markdown("---")
        st.markdown("### Sample Symbols to Try")
        sample_symbols = [
            "getABsub",
            "sum_haz",
            "hazSUBX",
            "getGeom",
            "zhao",
        ]

        cols = st.columns(len(sample_symbols))
        for i, sample in enumerate(sample_symbols):
            if cols[i].button(sample, key=f"symbol_sample_{i}"):
                st.session_state["symbol_input"] = sample
                st.rerun()

        st.markdown(
            """
            ---

            **What this does:**
            - Looks up a Fortran SUBROUTINE, FUNCTION, or MODULE by name
            - Generates an AI explanation of what the code does
            - Shows where this symbol is called (call graph)
            - Estimates the impact of changes (blast radius)
            """
        )

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

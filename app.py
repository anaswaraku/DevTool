"""
app.py — SmartDevTool Streamlit UI
Dark-themed, premium interface for scraping API docs and querying them with AI.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import json
from datetime import datetime

from src.agent import SmartAgent
from src.storage import StorageManager
from src.query import QueryEngine

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartDevTool",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Typography & Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Base dark background ── */
.stApp {
    background: #0d0f18;
    color: #e2e8f0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827 0%, #0d0f18 100%);
    border-right: 1px solid #1e2535;
}
[data-testid="stSidebar"] .stMarkdown h1 {
    color: #a78bfa;
}

/* ── Cards ── */
.sdt-card {
    background: #161b2e;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 14px;
    transition: box-shadow 0.25s ease;
}
.sdt-card:hover {
    box-shadow: 0 0 0 1px #7c3aed55, 0 8px 30px rgba(124,58,237,0.12);
}

/* ── Metric cards ── */
.sdt-metric {
    background: linear-gradient(135deg, #1a1f35 0%, #161b2e 100%);
    border: 1px solid #2d3561;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.sdt-metric .value {
    font-size: 2rem;
    font-weight: 700;
    color: #a78bfa;
    line-height: 1.1;
}
.sdt-metric .label {
    font-size: 0.78rem;
    color: #7b8ab8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 4px;
}

/* ── HTTP Method badges ── */
.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 5px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.05em;
}
.badge-GET    { background: #064e3b; color: #34d399; border: 1px solid #059669; }
.badge-POST   { background: #1e3a5f; color: #60a5fa; border: 1px solid #2563eb; }
.badge-PUT    { background: #431407; color: #fb923c; border: 1px solid #ea580c; }
.badge-DELETE { background: #450a0a; color: #f87171; border: 1px solid #dc2626; }
.badge-PATCH  { background: #3b2006; color: #fbbf24; border: 1px solid #d97706; }
.badge-HEAD   { background: #1a1a2e; color: #a78bfa; border: 1px solid #7c3aed; }
.badge-OPTIONS{ background: #1a1a2e; color: #94a3b8; border: 1px solid #475569; }

/* ── Tool badge ── */
.tool-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    background: #2d1b69;
    color: #c4b5fd;
    border: 1px solid #5b21b6;
}

/* ── Auth card ── */
.auth-card {
    background: #0f1a2e;
    border: 1px solid #1e3a5f;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
}

/* ── Endpoint row ── */
.ep-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    background: #111827;
    border: 1px solid #1e2535;
    border-radius: 8px;
    margin-bottom: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    transition: background 0.15s;
}
.ep-row:hover { background: #1a2235; }
.ep-path { color: #e2e8f0; flex: 1; }
.ep-desc { color: #6b7fa3; font-size: 0.75rem; font-family: 'Inter', sans-serif; }

/* ── Code blocks ── */
.code-block {
    background: #0a0e1a;
    border: 1px solid #1e2535;
    border-radius: 8px;
    padding: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #a5f3fc;
    white-space: pre-wrap;
    overflow-x: auto;
    margin-bottom: 12px;
}

/* ── Streamlit input overrides ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #111827 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 2px rgba(124,58,237,0.25) !important;
}

/* ── Button overrides ── */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #6d28d9) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #8b5cf6, #7c3aed) !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.35) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #111827;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
    border: 1px solid #1e2535;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #7b8ab8 !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
    background: #2d1b69 !important;
    color: #c4b5fd !important;
}

/* ── Dividers ── */
hr { border-color: #1e2535 !important; }

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: #111827 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}

/* ── Animations ── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeIn 0.4s ease both; }

/* ── Success / Error ── */
.sdt-success {
    background: #052e16;
    border: 1px solid #166534;
    border-radius: 8px;
    padding: 12px 16px;
    color: #4ade80;
    font-size: 0.9rem;
}
.sdt-error {
    background: #2d0a0a;
    border: 1px solid #7f1d1d;
    border-radius: 8px;
    padding: 12px 16px;
    color: #f87171;
    font-size: 0.9rem;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d0f18; }
::-webkit-scrollbar-thumb { background: #2d3561; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #7c3aed; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

TOOL_ICONS = {
    "beautifulsoup": "🍜",
    "scrapy":        "🕷️",
    "selenium":      "🌐",
    "octoparse":     "🔮",
}

METHOD_ORDER = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def method_badge(method: str) -> str:
    m = method.upper()
    return f'<span class="badge badge-{m}">{m}</span>'


def tool_badge_html(tool: str) -> str:
    icon = TOOL_ICONS.get(tool, "🔧")
    return f'<span class="tool-badge">{icon} {tool.title()}</span>'


def metric_card(value, label: str) -> str:
    return f"""
    <div class="sdt-metric">
        <div class="value">{value}</div>
        <div class="label">{label}</div>
    </div>"""


def fmt_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return ts


# ── Session state init ─────────────────────────────────────────────────────────

if "active_app_id" not in st.session_state:
    st.session_state.active_app_id = None
if "scrape_status" not in st.session_state:
    st.session_state.scrape_status = None  # "success" | "error" | None
if "scrape_msg" not in st.session_state:
    st.session_state.scrape_msg = ""


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 20px 0;">
        <div style="font-size:1.7rem; font-weight:800; color:#a78bfa; letter-spacing:-0.5px;">
            ⚡ SmartDevTool
        </div>
        <div style="font-size:0.78rem; color:#4b5880; margin-top:2px;">
            AI-powered API documentation scraper
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Add New App ──
    with st.expander("➕  Add New App", expanded=True):
        url_input = st.text_input(
            "Documentation URL",
            placeholder="https://docs.example.com/api/",
            key="url_input",
            label_visibility="visible",
        )
        name_input = st.text_input(
            "App Name",
            placeholder="e.g. Stripe, GitHub, Notion",
            key="name_input",
        )

        if st.button("🚀  Scrape Now", use_container_width=True, key="btn_scrape"):
            if not url_input.strip():
                st.warning("Please enter a URL.")
            elif not name_input.strip():
                st.warning("Please enter an app name.")
            else:
                with st.spinner("🤖 Agent inspecting site & selecting tool…"):
                    try:
                        agent = SmartAgent()
                        result, record = agent.run(
                            url_input.strip(), name_input.strip()
                        )
                        rec_id = record.id if hasattr(record, "id") else record["id"]
                        st.session_state.active_app_id = rec_id

                        if result.error:
                            st.session_state.scrape_status = "warning"
                            st.session_state.scrape_msg = (
                                f"⚠️ Scraped with **{result.tool_used}** but encountered an issue:\n\n"
                                f"`{result.error}`"
                            )
                        else:
                            st.session_state.scrape_status = "success"
                            ep_count = len(result.endpoints)
                            sec_count = len([k for k in result.raw_sections if not k.startswith("__")])
                            st.session_state.scrape_msg = (
                                f"✅ Scraped with **{result.tool_used}** · "
                                f"**{ep_count}** endpoints · "
                                f"**{sec_count}** sections · "
                                f"ID: `{rec_id}`"
                            )
                    except Exception as ex:
                        st.session_state.scrape_status = "error"
                        st.session_state.scrape_msg = str(ex)
                st.rerun()

    # Status message after scrape
    if st.session_state.scrape_status == "success":
        st.markdown(
            f'<div class="sdt-success">{st.session_state.scrape_msg}</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.scrape_status == "warning":
        st.warning(st.session_state.scrape_msg)
    elif st.session_state.scrape_status == "error":
        st.markdown(
            f'<div class="sdt-error">❌ {st.session_state.scrape_msg}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Saved Apps ──
    storage = StorageManager()
    apps = storage.list_apps()

    st.markdown(
        f'<div style="font-size:0.82rem;color:#4b5880;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">📚 Saved Apps ({len(apps)})</div>',
        unsafe_allow_html=True,
    )

    if not apps:
        st.markdown(
            '<div style="color:#374151;font-size:0.85rem;padding:8px 0;">No apps scraped yet.</div>',
            unsafe_allow_html=True,
        )
    else:
        for app in apps:
            app_id = app["id"]
            ep_count = app.get("endpoint_count", 0)
            ep_label = f" ({ep_count} ep)" if ep_count > 0 else " (empty)"
            label = f"{TOOL_ICONS.get(app['tool_used'], '🔧')} {app['app_name']}{ep_label}"
            col1, col2 = st.columns([5, 1])
            with col1:
                is_active = app_id == st.session_state.active_app_id
                btn_style = "background:#2d1b69!important;" if is_active else ""
                if st.button(label, key=f"sel_{app_id}", use_container_width=True):
                    st.session_state.active_app_id = app_id
                    st.session_state.scrape_status = None
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"del_{app_id}", help="Delete"):
                    storage.delete(app_id)
                    if st.session_state.active_app_id == app_id:
                        st.session_state.active_app_id = None
                    st.rerun()


# ── Main Panel ─────────────────────────────────────────────────────────────────

active_id = st.session_state.active_app_id

if active_id is None:
    # ── Welcome / empty state ──
    st.markdown("""
    <div class="fade-in" style="text-align:center; padding: 80px 40px;">
        <div style="font-size: 4rem; margin-bottom: 16px;">⚡</div>
        <h1 style="color:#a78bfa; font-size:2.2rem; font-weight:800; margin-bottom:8px;">
            SmartDevTool
        </h1>
        <p style="color:#4b5880; font-size:1.05rem; max-width:520px; margin:0 auto 32px;">
            Paste any API documentation URL in the sidebar. The AI agent will
            pick the best scraping tool automatically, extract endpoints,
            auth methods and code snippets — then let you query it in plain English.
        </p>
        <div style="display:flex; gap:16px; justify-content:center; flex-wrap:wrap;">
    """ + "".join([
        f'<div class="sdt-card" style="width:160px;text-align:center;padding:20px 16px;">'
        f'<div style="font-size:2rem;">{icon}</div>'
        f'<div style="color:#a78bfa;font-weight:600;font-size:0.9rem;margin-top:8px;">{name.title()}</div>'
        f'<div style="color:#4b5880;font-size:0.75rem;margin-top:4px;">{desc}</div>'
        f'</div>'
        for name, icon, desc in [
            ("beautifulsoup", "🍜", "Static HTML"),
            ("scrapy",        "🕷️",  "Multi-page crawl"),
            ("selenium",      "🌐", "JS-rendered / SPA"),
            ("octoparse",     "🔮", "Visual / complex"),
        ]
    ]) + """
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # ── Load app data ──
    try:
        app_data = storage.load(active_id)
        app_record = storage.get_record(active_id)
    except FileNotFoundError:
        st.error(f"Data file for `{active_id}` not found. It may have been deleted.")
        st.session_state.active_app_id = None
        st.stop()

    # ── App header ──
    col_title, col_badge = st.columns([6, 2])
    with col_title:
        st.markdown(
            f'<h1 style="color:#f1f5f9;font-size:1.8rem;font-weight:800;margin-bottom:4px;">'
            f'{app_data.get("app_name", "Unknown App")}</h1>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<a href="{app_data.get("url","")}" target="_blank" '
            f'style="color:#7b8ab8;font-size:0.85rem;text-decoration:none;">'
            f'🔗 {app_data.get("url","")}</a>',
            unsafe_allow_html=True,
        )
    with col_badge:
        st.markdown(
            f'<div style="text-align:right;padding-top:8px;">'
            f'{tool_badge_html(app_data.get("tool_used",""))}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Metric row ──
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(metric_card(len(app_data.get("endpoints", [])), "Endpoints"), unsafe_allow_html=True)
    with m2:
        st.markdown(metric_card(len(app_data.get("auth_methods", [])), "Auth Methods"), unsafe_allow_html=True)
    with m3:
        st.markdown(metric_card(len(app_data.get("sample_urls", [])), "Sample URLs"), unsafe_allow_html=True)
    with m4:
        visible_sections = [k for k in app_data.get("raw_sections", {}) if not k.startswith("__")]
        st.markdown(metric_card(len(visible_sections), "Doc Sections"), unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Tabs ──
    tab_overview, tab_endpoints, tab_auth, tab_wrappers, tab_query = st.tabs(
        ["📋  Overview", "🔌  Endpoints", "🔑  Auth", "💻  Code", "🤖  Ask AI"]
    )

    # ============================================================
    # TAB 1 — Overview
    # ============================================================
    with tab_overview:
        sections = app_data.get("raw_sections", {})

        # Separate private (full_text) from named sections
        named_sections = {k: v for k, v in sections.items() if not k.startswith("__") and v}
        full_text = sections.get("__full_text__", "")

        if named_sections:
            st.markdown("### Documentation Sections")
            for title, content in list(named_sections.items())[:15]:
                with st.expander(f"📄 {title}"):
                    st.markdown(
                        f'<div style="color:#94a3b8;font-size:0.88rem;line-height:1.7;">'
                        f'{content[:2000]}</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                '<div style="color:#4b5880;">No named sections extracted.</div>',
                unsafe_allow_html=True,
            )

        if app_data.get("use_cases"):
            st.markdown("### Use Cases")
            for uc in app_data["use_cases"]:
                st.markdown(
                    f'<div class="sdt-card">💡 {uc}</div>',
                    unsafe_allow_html=True,
                )

        # Show the raw full-text dump at the bottom for transparency
        if full_text:
            st.markdown("---")
            with st.expander("📝 Raw page text (used for AI queries)", expanded=False):
                st.markdown(
                    f'<div style="color:#64748b;font-size:0.8rem;font-family:monospace;white-space:pre-wrap;line-height:1.5;">'
                    f'{full_text[:3000]}</div>',
                    unsafe_allow_html=True,
                )

    # ============================================================
    # TAB 2 — Endpoints
    # ============================================================
    with tab_endpoints:
        endpoints = app_data.get("endpoints", [])
        if not endpoints:
            st.markdown(
                '<div class="sdt-card" style="border-left:4px solid #7c3aed;text-align:center;padding:32px;">'
                '<div style="font-size:2rem;margin-bottom:8px">🤖</div>'
                '<div style="color:#a78bfa;font-weight:600;font-size:1rem;margin-bottom:6px;">No structured endpoints found</div>'
                '<div style="color:#6b7fa3;font-size:0.85rem;">'
                'This site renders endpoints via JavaScript or uses a non-standard layout.<br>'
                'Switch to the <strong style="color:#c4b5fd">Ask AI</strong> tab and ask: '
                '<em>\'What endpoints are available?\'</em> — the LLM will extract them from the raw text.'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            # Filter controls
            filter_col, method_col = st.columns([3, 2])
            with filter_col:
                search = st.text_input(
                    "Filter endpoints",
                    placeholder="Search path or method…",
                    key="ep_search",
                    label_visibility="collapsed",
                )
            with method_col:
                method_filter = st.multiselect(
                    "Methods",
                    options=METHOD_ORDER,
                    default=[],
                    key="ep_methods",
                    label_visibility="collapsed",
                    placeholder="All methods",
                )

            st.markdown(f"<div style='color:#4b5880;font-size:0.8rem;margin-bottom:12px;'>{len(endpoints)} endpoints total</div>", unsafe_allow_html=True)

            displayed = 0
            for ep in endpoints:
                method = ep.get("method", "?").upper()
                path = ep.get("path", "")
                desc = ep.get("description", "")

                if method_filter and method not in method_filter:
                    continue
                if search and search.lower() not in path.lower() and search.lower() not in method.lower():
                    continue

                desc_part = f'<span class="ep-desc"> — {desc}</span>' if desc else ""
                st.markdown(
                    f'<div class="ep-row">'
                    f'{method_badge(method)}'
                    f'<span class="ep-path">{path}</span>'
                    f'{desc_part}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                displayed += 1

            if displayed == 0:
                st.markdown(
                    '<div style="color:#4b5880;padding:10px 0;">No endpoints match your filter.</div>',
                    unsafe_allow_html=True,
                )

    # ============================================================
    # TAB 3 — Auth
    # ============================================================
    with tab_auth:
        auth_methods = app_data.get("auth_methods", [])
        if not auth_methods:
            st.markdown(
                '<div style="color:#4b5880;padding:20px 0;">No authentication methods detected.</div>',
                unsafe_allow_html=True,
            )
        else:
            for auth in auth_methods:
                atype = auth.get("type", "Unknown")
                adesc = auth.get("description", "")
                st.markdown(
                    f'<div class="auth-card">'
                    f'<div style="font-weight:600;color:#60a5fa;font-size:0.95rem;">🔑 {atype}</div>'
                    f'<div style="color:#94a3b8;font-size:0.85rem;margin-top:6px;">{adesc}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        samples = app_data.get("sample_urls", [])
        if samples:
            st.markdown("### Sample API URLs")
            for url in samples:
                st.markdown(
                    f'<div class="code-block">{url}</div>',
                    unsafe_allow_html=True,
                )

    # ============================================================
    # TAB 4 — Code / Wrapper Hints
    # ============================================================
    with tab_wrappers:
        hints = app_data.get("wrapper_hints", [])
        if not hints:
            st.markdown(
                '<div style="color:#4b5880;padding:20px 0;">No code snippets extracted.</div>',
                unsafe_allow_html=True,
            )
        else:
            for i, snippet in enumerate(hints, 1):
                st.markdown(f"**Snippet {i}**")
                st.code(snippet, language="python")
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Raw JSON download
        st.markdown("---")
        st.markdown("### Raw Scraped Data")
        st.download_button(
            label="⬇️  Download JSON",
            data=json.dumps(app_data, indent=2, ensure_ascii=False),
            file_name=f"{active_id}.json",
            mime="application/json",
            use_container_width=True,
        )

    # ============================================================
    # TAB 5 — Ask AI
    # ============================================================
    with tab_query:
        st.markdown(
            '<div style="color:#7b8ab8;font-size:0.88rem;margin-bottom:16px;">'
            'Ask any question about this API. The AI answers using only the scraped documentation.</div>',
            unsafe_allow_html=True,
        )

        # Quick question chips
        st.markdown("**Quick questions:**")
        chip_cols = st.columns(3)
        quick_qs = [
            "What endpoints are available?",
            "How do I authenticate?",
            "Show me a code example",
            "What are the main use cases?",
            "What HTTP methods are used?",
            "Summarise this API",
        ]
        if "ai_question" not in st.session_state:
            st.session_state.ai_question = ""

        for i, q in enumerate(quick_qs):
            with chip_cols[i % 3]:
                if st.button(q, key=f"chip_{i}", use_container_width=True):
                    st.session_state.ai_question = q
                    st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        question = st.text_area(
            "Your question",
            value=st.session_state.ai_question,
            placeholder="e.g. How do I create a new user via the API?",
            height=90,
            key="question_input",
            label_visibility="collapsed",
        )

        if st.button("🤖  Ask AI", use_container_width=True, key="btn_ask"):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Thinking…"):
                    try:
                        engine = QueryEngine()
                        answer = engine.answer(app_data, question.strip())
                        st.markdown("---")
                        st.markdown(
                            '<div style="color:#a78bfa;font-weight:600;font-size:0.85rem;'
                            'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">'
                            '🤖 AI Answer</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(answer)
                        st.session_state.ai_question = ""
                    except Exception as ex:
                        st.error(f"LLM error: {ex}")

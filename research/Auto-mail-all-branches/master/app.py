"""
Job Application Email Reply Assistant — Streamlit App
"""
import streamlit as st
from dotenv import load_dotenv

from utils.email_parser import extract_email
from utils.pdf_reader import extract_text_from_pdf
from utils.llm import generate_reply, generate_linkedin_dm
from utils.email_sender import send_email

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Auto-Email | Job Reply Assistant",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Full-width container */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        padding-top: 0.5rem !important;
    }

    /* Dark gradient background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
        color: #e2e8f0;
    }

    /* Header */
    .hero {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem;
    }
    .hero h1 {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .hero p {
        color: #94a3b8;
        font-size: 1.05rem;
    }

    /* Cards */
    .card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.5rem 1.5rem 1rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(12px);
    }
    .card-title {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #818cf8;
        margin-bottom: 0.6rem;
    }

    /* Buttons */
    div[data-testid="stButton"] > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0.65rem 1.2rem;
        transition: all 0.2s ease;
    }
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #818cf8, #c084fc);
        border: none;
        color: #fff;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        opacity: 0.88;
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(129,140,248,0.4);
    }
    div[data-testid="stButton"] > button:not([kind="primary"]) {
        background: linear-gradient(135deg, #10b981, #059669);
        border: none;
        color: #fff;
    }
    div[data-testid="stButton"] > button:not([kind="primary"]):hover {
        opacity: 0.88;
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(16,185,129,0.4);
    }

    /* Text areas */
    .stTextArea textarea {
        background: rgba(15,12,41,0.6) !important;
        border: 1px solid rgba(129,140,248,0.3) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
        font-size: 0.9rem !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextArea textarea:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 0 2px rgba(129,140,248,0.2) !important;
    }

    /* Text inputs */
    .stTextInput input {
        background: rgba(15,12,41,0.6) !important;
        border: 1px solid rgba(129,140,248,0.3) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
        font-size: 0.9rem !important;
    }
    .stTextInput input:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 0 2px rgba(129,140,248,0.2) !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px dashed rgba(129,140,248,0.4) !important;
        border-radius: 10px !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 500;
        border: 1px solid rgba(255,255,255,0.08);
        padding: 0.4rem 1.2rem;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(129,140,248,0.25), rgba(192,132,252,0.25)) !important;
        color: #c084fc !important;
        border-color: rgba(192,132,252,0.4) !important;
    }

    /* Divider */
    hr { border-color: rgba(255,255,255,0.08); }

    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 0.3rem 0.8rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .badge-ready {
        background: rgba(16,185,129,0.15);
        color: #10b981;
        border: 1px solid rgba(16,185,129,0.3);
    }
    .badge-empty {
        background: rgba(148,163,184,0.1);
        color: #64748b;
        border: 1px solid rgba(148,163,184,0.15);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Hero Header ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <h1>✉️ Auto-Email</h1>
        <p>Craft perfectly tailored job application replies in seconds — powered by AI</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()

# ── Session state defaults ────────────────────────────────────────────────────
if "email_output_area" not in st.session_state:
    st.session_state["email_output_area"] = ""
if "linkedin_dm_area" not in st.session_state:
    st.session_state["linkedin_dm_area"] = ""
if "auto_recipient" not in st.session_state:
    st.session_state["auto_recipient"] = ""
if "subject_input" not in st.session_state:
    st.session_state["subject_input"] = "Re: Job Opportunity"
if "manual_recipient" not in st.session_state:
    st.session_state["manual_recipient"] = ""

# ── Layout: two columns ───────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

# ═══════════════════════════════════════════════════════════════════════════════
# LEFT — INPUTS
# ═══════════════════════════════════════════════════════════════════════════════
with left:
    st.markdown("### 📥 Inputs")

    # 1. Resume — tab between paste and upload
    st.markdown('<div class="card-title">📄 Your Resume</div>', unsafe_allow_html=True)
    r_tab1, r_tab2 = st.tabs(["Paste Text", "Upload PDF"])
    with r_tab1:
        resume_text_input = st.text_area(
            label="resume_paste",
            label_visibility="collapsed",
            placeholder="Paste your resume as plain text…",
            height=200,
            key="resume_text_area",
        )
    with r_tab2:
        uploaded_pdf = st.file_uploader(
            "Upload your resume (PDF)",
            type=["pdf"],
            key="resume_pdf",
            label_visibility="collapsed",
        )
        if uploaded_pdf:
            st.success(f"✅ **{uploaded_pdf.name}** uploaded")

    # 2. Recruiter Email / Job Description (combined field)
    st.markdown(
        '<div class="card-title" style="margin-top:1rem">💼 Recruiter Email / Job Description</div>',
        unsafe_allow_html=True,
    )
    st.caption("Paste the email or message from the recruiter. The recipient's email will be auto-extracted.")
    jd = st.text_area(
        label="jd",
        label_visibility="collapsed",
        placeholder="Paste the recruiter's email or job description here…",
        height=260,
        key="jd_input",
    )

    # Live email extraction from JD field
    live_email = extract_email(jd) if jd.strip() else None
    if live_email and live_email != st.session_state["auto_recipient"]:
        st.session_state["auto_recipient"] = live_email

    st.markdown("<br>", unsafe_allow_html=True)

    # Readiness badges
    def _badge(label: str, ready: bool) -> str:
        cls = "badge-ready" if ready else "badge-empty"
        icon = "✓" if ready else "○"
        return f'<span class="status-badge {cls}">{icon} {label}</span>&nbsp;&nbsp;'

    resume_ready = bool(resume_text_input.strip()) or uploaded_pdf is not None
    badge_html = (
        _badge("Resume", resume_ready)
        + _badge("Recruiter Email / JD", bool(jd.strip()))
    )
    st.markdown(badge_html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    generate_btn = st.button("🪄 Generate Reply", type="primary", key="gen_btn")

# ═══════════════════════════════════════════════════════════════════════════════
# RIGHT — OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════
with right:
    st.markdown("### ✏️ Draft & Send")

    # ── Generate logic ─────────────────────────────────────────────────────────
    if generate_btn:
        # Resolve resume text
        resume_final = resume_text_input.strip()
        if not resume_final and uploaded_pdf:
            resume_final = extract_text_from_pdf(uploaded_pdf.getvalue())

        missing = []
        if not resume_final:
            missing.append("Resume")
        if not jd.strip():
            missing.append("Recruiter Email / JD")

        if missing:
            st.error(f"⚠️ Please fill in: **{', '.join(missing)}**")
        else:
            with st.spinner("🤖 Generating your personalized reply…"):
                try:
                    subject, body = generate_reply(
                        resume=resume_final,
                        jd=jd.strip(),
                    )
                    st.session_state["email_output_area"] = body
                    st.session_state["subject_input"] = subject
                    st.session_state["auto_recipient"] = extract_email(jd) or ""
                    st.success("✨ Email generated! Review, edit, then send.")
                except Exception as exc:
                    st.error(f"❌ Generation failed: {exc}")

    # ── Editable output ────────────────────────────────────────────────────────
    st.markdown('<div class="card-title">Generated Email (editable)</div>', unsafe_allow_html=True)
    edited_email = st.text_area(
        label="generated_email_output",
        label_visibility="collapsed",
        placeholder="Your AI-generated reply will appear here. You can edit it before sending.",
        height=300,
        key="email_output_area",
    )

    # ── Send section ───────────────────────────────────────────────────────────
    st.markdown('<div class="card-title" style="margin-top:1rem">📮 Send</div>', unsafe_allow_html=True)

    auto_recipient = st.session_state["auto_recipient"]

    if auto_recipient:
        st.markdown(
            f'<div style="font-size:0.85rem;margin-bottom:0.6rem;padding:0.5rem 0.75rem;'
            f'background:rgba(129,140,248,0.12);border:1px solid rgba(129,140,248,0.3);'
            f'border-radius:8px;color:#94a3b8;">'
            f'📧 Sending to: <span style="color:#818cf8;font-weight:600;">{auto_recipient}</span></div>',
            unsafe_allow_html=True,
        )
        recipient = auto_recipient
    else:
        st.caption("⚠️ No email address found in the recruiter message. Enter it manually:")
        recipient = st.text_input(
            "Recipient Email",
            placeholder="recruiter@company.com",
            key="manual_recipient",
        )

    subject = st.text_input(
        "Subject",
        placeholder="Re: …",
        key="subject_input",
    )

    # Show PDF attachment status
    if uploaded_pdf:
        st.caption(f"📎 **{uploaded_pdf.name}** will be attached to the email.")
    else:
        st.caption("ℹ️ Upload a PDF resume to automatically attach it to the email.")

    send_btn = st.button("📤 Send Email", type="primary", key="send_btn")

    if send_btn:
        if not edited_email.strip():
            st.error("⚠️ The email body is empty. Please generate or write an email first.")
        elif not recipient or not recipient.strip():
            st.error("⚠️ Please enter the recruiter's email address.")
        else:
            with st.spinner("📬 Sending…"):
                try:
                    pdf_bytes = uploaded_pdf.getvalue() if uploaded_pdf else None
                    pdf_name = uploaded_pdf.name if uploaded_pdf else "resume.pdf"
                    send_email(
                        to=recipient.strip(),
                        subject=st.session_state["subject_input"] or "Re: Job Opportunity",
                        body=edited_email.strip(),
                        attachment_bytes=pdf_bytes,
                        attachment_name=pdf_name,
                    )
                    st.success(f"🎉 Email sent successfully to {recipient.strip()}!")
                    st.balloons()
                except ValueError as ve:
                    st.error(f"⚙️ Configuration error: {ve}")
                except Exception as exc:
                    st.error(f"❌ Failed to send: {exc}")

    st.divider()

    # ── LinkedIn DM section ────────────────────────────────────────────────────
    st.markdown('<div class="card-title">💼 LinkedIn DM</div>', unsafe_allow_html=True)
    st.caption("Generate a short LinkedIn message to send to the recruiter.")

    linkedin_btn = st.button("✍️ Generate LinkedIn DM", key="linkedin_btn")

    if linkedin_btn:
        resume_val = st.session_state.get("resume_text_area", "").strip()
        if not resume_val and uploaded_pdf:
            resume_val = extract_text_from_pdf(uploaded_pdf.getvalue())
        jd_val = st.session_state.get("jd_input", "").strip()

        if not resume_val or not jd_val:
            st.error("⚠️ Please fill in Resume and Recruiter Email / JD before generating the LinkedIn DM.")
        else:
            with st.spinner("✍️ Crafting LinkedIn DM…"):
                try:
                    dm = generate_linkedin_dm(resume=resume_val, jd=jd_val)
                    st.session_state["linkedin_dm_area"] = dm
                except Exception as exc:
                    st.error(f"❌ LinkedIn DM generation failed: {exc}")

    st.text_area(
        label="linkedin_dm_output",
        label_visibility="collapsed",
        placeholder="Your LinkedIn DM will appear here. Copy and send it on LinkedIn.",
        height=220,
        key="linkedin_dm_area",
    )

    st.warning(
        "⚠️ **Remember:** LinkedIn does not support email attachments. "
        "After sending this DM, **manually attach your resume** as a follow-up message or share a Google Drive / OneDrive link.",
        icon="📎",
    )


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    '<p style="text-align:center;color:#475569;font-size:0.78rem;">'
    "Auto-Email · Powered by Groq (Llama 3.3 70B) · Emails sent via Gmail SMTP"
    "</p>",
    unsafe_allow_html=True,
)

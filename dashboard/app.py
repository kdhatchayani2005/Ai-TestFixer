import os
import re
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

# Add root folder to sys.path
ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from database import db_manager

# Page Configuration - Set to Wide mode for premium layout
st.set_page_config(
    page_title="AI TestFixer Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark-compatible premium styling
st.markdown("""
<style>
    /* Premium style metrics and cards */
    .metric-card {
        background-color: #1e293b;
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.6);
    }
    .metric-val {
        font-size: 32px;
        font-weight: 700;
        color: #818cf8;
        margin-bottom: 4px;
    }
    .metric-lbl {
        font-size: 13px;
        font-weight: 500;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .custom-title {
        font-size: 38px;
        font-weight: 700;
        background: linear-gradient(to right, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }
    /* Style headers */
    h1, h2, h3 {
        color: #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DB structure on load
db_manager.init_db()

# Navigation setup via sidebar radio options
st.sidebar.title("🤖 AI TestFixer")
st.sidebar.markdown("*Self-Healing Framework*")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation Menu",
    [
        "Home",
        "Healing History",
        "Failure Analytics",
        "Screenshot Viewer",
        "Execution Logs",
        "AI Recommendations",
        "Prompt Documentation",
        "Performance Metrics",
        "Healing Leaderboard"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("System Status: **Active**")
st.sidebar.caption(f"Local Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Helper: PDF Exporter using ReportLab
def generate_pdf_report(kpis, history_df):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    
    reports_dir = ROOT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = reports_dir / "test_report.pdf"
    
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("AI TestFixer Execution Report", styles["Title"]))
    story.append(Spacer(1, 15))
    
    # Timestamp
    time_style = ParagraphStyle('TimeStyle', parent=styles['Normal'], textColor=colors.HexColor('#64748b'))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", time_style))
    story.append(Spacer(1, 20))
    
    # KPIs Table
    kpi_data = [
        [Paragraph("<b>Metric</b>", styles["Normal"]), Paragraph("<b>Value</b>", styles["Normal"])],
        ["Total Tests Run", str(kpis["total"])],
        ["Passed Tests", str(kpis["passed"])],
        ["Failed Tests", str(kpis["failed"])],
        ["Healed Tests", str(kpis["healed"])],
        ["Avg Heal Time", f"{kpis['avg_heal_time']}s"]
    ]
    t = Table(kpi_data, colWidths=[200, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white])
    ]))
    story.append(t)
    story.append(Spacer(1, 25))
    
    # History Table
    story.append(Paragraph("Recent Test History", styles["Heading2"]))
    story.append(Spacer(1, 10))
    
    history_headers = ["ID", "Test Name", "Status", "Duration", "Healed"]
    history_data = [[Paragraph(f"<b>{h}</b>", styles["Normal"]) for h in history_headers]]
    
    for idx, row in history_df.iterrows():
        history_data.append([
            str(row.get("id", "")),
            str(row.get("test_name", "")),
            str(row.get("status", "")),
            f"{row.get('execution_time', 0.0):.2f}s",
            "Yes" if row.get("healed", 0) == 1 else "No"
        ])
        
    if len(history_data) > 1:
        th = Table(history_data, colWidths=[50, 150, 100, 100, 100])
        th.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white])
        ]))
        story.append(th)
    else:
        story.append(Paragraph("No test execution records found.", styles["Normal"]))
        
    doc.build(story)
    return pdf_path

# ==============================================================================
# PAGE 1 — Home  (File-Upload Driven — No Hardcoded Defaults)
# ==============================================================================
if page == "Home":
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10000, key="homerefresh")

    st.markdown("<div class='custom-title'>AI TestFixer Analytics Hub</div>", unsafe_allow_html=True)
    st.write("Upload your test execution CSV file or run tests to populate the dashboard with live metrics.")

    # ── File Upload Section ────────────────────────────────────────────────────
    st.markdown("### Upload Test Execution Data")
    st.markdown("""
    <div style='background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.3);
                border-radius: 10px; padding: 16px; margin-bottom: 20px;'>
        <b>Accepted Format:</b> CSV file with columns:
        <code>test_name, status, execution_time, healed</code><br>
        <b>status values:</b> <code>PASS</code> or <code>FAIL</code> &nbsp;|&nbsp;
        <b>healed values:</b> <code>0</code> (not healed) or <code>1</code> (healed)<br>
        <b>execution_time:</b> float in seconds (e.g. <code>3.45</code>)
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Drop your CSV file here or click to browse",
        type=["csv"],
        key="home_file_uploader",
        help="Upload a CSV with columns: test_name, status, execution_time, healed"
    )

    # Provide a downloadable template CSV
    template_csv = "test_name,status,execution_time,healed\nlogin_test,PASS,3.21,0\nlogin_test,FAIL,6.84,0\nlogin_test,PASS,5.12,1\n"
    st.download_button(
        label="📋 Download CSV Template",
        data=template_csv.encode("utf-8"),
        file_name="test_data_template.csv",
        mime="text/csv"
    )

    st.markdown("---")

    # ── Process Uploaded File ──────────────────────────────────────────────────
    if uploaded_file is not None:
        try:
            upload_df = pd.read_csv(uploaded_file)

            # Validate required columns
            required_cols = {"test_name", "status", "execution_time", "healed"}
            missing_cols = required_cols - set(upload_df.columns.str.lower().tolist())

            if missing_cols:
                st.error(f"CSV is missing required columns: **{', '.join(missing_cols)}**. Please fix your file and re-upload.")
            else:
                # Normalize column names to lowercase
                upload_df.columns = upload_df.columns.str.lower()

                # Validate status values
                valid_statuses = {"PASS", "FAIL"}
                invalid_statuses = set(upload_df["status"].str.upper().unique()) - valid_statuses
                if invalid_statuses:
                    st.warning(f"Unknown status values found: **{invalid_statuses}**. Only PASS and FAIL are recognized.")

                # Show preview of uploaded data
                st.success(f"File uploaded successfully! **{len(upload_df)} records** found.")
                with st.expander("Preview Uploaded Data", expanded=True):
                    st.dataframe(upload_df, use_container_width=True)

                # ── Import button ──────────────────────────────────────────────
                col_import, col_clear = st.columns([2, 1])
                with col_import:
                    if st.button("Import into Database & Refresh Metrics", type="primary"):
                        imported = 0
                        errors = 0
                        for _, row in upload_df.iterrows():
                            try:
                                db_manager.insert_test_history(
                                    test_name=str(row["test_name"]).strip(),
                                    status=str(row["status"]).strip().upper(),
                                    execution_time=float(row["execution_time"]),
                                    healed=int(row["healed"])
                                )
                                imported += 1
                            except Exception as row_err:
                                errors += 1

                        if imported > 0:
                            st.success(f"Successfully imported **{imported} records** into the database!")
                        if errors > 0:
                            st.warning(f"{errors} rows could not be imported due to data format issues.")
                        st.rerun()

                with col_clear:
                    if st.button("Clear All DB Records", type="secondary"):
                        conn = db_manager.get_connection()
                        conn.execute("DELETE FROM test_history")
                        conn.execute("DELETE FROM failures")
                        conn.execute("DELETE FROM learned_fixes")
                        conn.execute("DELETE FROM performance")
                        conn.execute("DELETE FROM alerts")
                        conn.execute("DELETE FROM retry_log")
                        conn.commit()
                        conn.close()
                        st.success("All database records cleared.")
                        st.rerun()

        except Exception as parse_err:
            st.error(f"Could not parse uploaded file: {str(parse_err)}")

    st.markdown("---")

    # ── KPI Cards — populated from live DB ────────────────────────────────────
    kpis = db_manager.get_kpi_stats()
    history_df = db_manager.get_all_test_history()

    if history_df.empty:
        st.info("No test execution data found. Upload a CSV file above or run `python tests/login_test.py --locator loginBtn` to generate live data.")
    else:
        st.markdown("### Live KPI Metrics")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"<div class='metric-card'><div class='metric-val'>{kpis['total']}</div><div class='metric-lbl'>Total Runs</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#10b981;'>{kpis['passed']}</div><div class='metric-lbl'>Passed</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#ef4444;'>{kpis['failed']}</div><div class='metric-lbl'>Failed</div></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#f59e0b;'>{kpis['healed']}</div><div class='metric-lbl'>Healed</div></div>", unsafe_allow_html=True)
        with col5:
            st.markdown(f"<div class='metric-card'><div class='metric-val'>{kpis['avg_heal_time']}s</div><div class='metric-lbl'>Avg Heal Time</div></div>", unsafe_allow_html=True)

        st.markdown("### Test Execution History")
        # Status color-coded display
        def style_status(val):
            if val == "PASS":
                return "background-color: rgba(16,185,129,0.15); color: #10b981; font-weight:600;"
            elif val == "FAIL":
                return "background-color: rgba(239,68,68,0.15); color: #ef4444; font-weight:600;"
            return ""

        styled_df = history_df.head(20).style.map(style_status, subset=["status"])
        st.dataframe(styled_df, use_container_width=True)

        # CSV export of current history
        csv_export = history_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download History as CSV",
            data=csv_export,
            file_name="test_history_export.csv",
            mime="text/csv"
        )

        st.markdown("---")

        # PDF Export
        if st.button("📄 Generate & Export PDF Report"):
            try:
                pdf_file_path = generate_pdf_report(kpis, history_df)
                st.success(f"PDF Report saved to: `reports/test_report.pdf`")
                with open(pdf_file_path, "rb") as f:
                    st.download_button(
                        label="Download PDF",
                        data=f.read(),
                        file_name="test_report.pdf",
                        mime="application/pdf"
                    )
            except Exception as err:
                st.error(f"PDF export error: {str(err)}")

# ==============================================================================
# PAGE 2 — Healing History
# ==============================================================================
elif page == "Healing History":
    st.markdown("<div class='custom-title'>Healed Locators Ledger</div>", unsafe_allow_html=True)
    st.write("Browse and manage healed locator configurations captured during test executions.")
    
    fixes_df = db_manager.get_all_learned_fixes()
    
    if fixes_df.empty:
        st.info("No self-healing history recorded. No learned fixes are present in SQLite database.")
    else:
        # Search filter
        search_query = st.text_input("🔍 Search locators (matches old or new locator strings):", "").strip()
        
        # Confidence slider filter
        min_confidence = st.slider("Filter by Confidence Threshold (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0)
        
        filtered_df = fixes_df[fixes_df["confidence"] >= min_confidence]
        
        if search_query:
            filtered_df = filtered_df[
                filtered_df["old_locator"].str.contains(search_query, case=False, na=False) |
                filtered_df["new_locator"].str.contains(search_query, case=False, na=False)
            ]
            
        if filtered_df.empty:
            st.info("No learned fixes match the search filters.")
        else:
            st.dataframe(filtered_df, use_container_width=True)
            
            # CSV Download Button
            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download List as CSV",
                data=csv_data,
                file_name="learned_fixes.csv",
                mime="text/csv"
            )

# ==============================================================================
# PAGE 3 — Failure Analytics
# ==============================================================================
elif page == "Failure Analytics":
    st.markdown("<div class='custom-title'>Failure Analytics & Visualization</div>", unsafe_allow_html=True)
    st.write("Aggregated breakdown charts representing failure profiles, statuses, and timeline distributions.")
    
    failures_df = db_manager.get_all_failures()
    history_df = db_manager.get_all_test_history()
    
    if failures_df.empty and history_df.empty:
        st.info("Insufficient failure data collected to generate charts.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            if not failures_df.empty:
                # 1. Bar chart: failures by error type
                err_counts = failures_df['error'].value_counts().reset_index()
                err_counts.columns = ['Error Type', 'Count']
                fig_err = px.bar(
                    err_counts,
                    x='Error Type',
                    y='Count',
                    title='Total Failures by Exception Type',
                    color='Error Type',
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    template='plotly_dark'
                )
                st.plotly_chart(fig_err, use_container_width=True)
            else:
                st.info("No exception logs found in the failures table.")
                
        with col2:
            if not history_df.empty:
                # 2. Pie chart: PASS vs FAIL vs HEALED status distribution
                def get_outcome(row):
                    if row['healed'] == 1:
                        return 'HEALED'
                    return row['status']
                
                history_df['outcome'] = history_df.apply(get_outcome, axis=1)
                outcome_counts = history_df['outcome'].value_counts().reset_index()
                outcome_counts.columns = ['Outcome', 'Count']
                
                fig_pie = px.pie(
                    outcome_counts,
                    values='Count',
                    names='Outcome',
                    title='Execution Outcome Distribution',
                    color='Outcome',
                    color_discrete_map={'PASS': '#10b981', 'FAIL': '#ef4444', 'HEALED': '#f59e0b'},
                    template='plotly_dark'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No execution runs logged in database.")
                
        # 3. Line chart: Failures per day over last 30 days
        if not failures_df.empty:
            # Parse timestamp and extract date
            failures_df['date'] = pd.to_datetime(failures_df['timestamp']).dt.date
            # Filter last 30 days
            min_date = (datetime.now() - pd.Timedelta(days=30)).date()
            failures_30 = failures_df[failures_df['date'] >= min_date]
            
            failures_by_date = failures_30.groupby('date').size().reset_index(name='Failures')
            # Sort by date
            failures_by_date = failures_by_date.sort_values('date')
            
            fig_trend = px.line(
                failures_by_date,
                x='date',
                y='Failures',
                title='30-Day Failure Trend',
                markers=True,
                line_shape='linear',
                color_discrete_sequence=['#818cf8'],
                template='plotly_dark'
            )
            st.plotly_chart(fig_trend, use_container_width=True)

# ==============================================================================
# PAGE 4 — Screenshot Viewer
# ==============================================================================
elif page == "Screenshot Viewer":
    st.markdown("<div class='custom-title'>Visual Defect Screenshots</div>", unsafe_allow_html=True)
    st.write("Browse and view screenshots captured automatically at the exact moment of failure.")
    
    screenshots_dir = ROOT_DIR / "screenshots"
    
    # Find all PNG files in directory
    png_files = []
    if screenshots_dir.exists():
        png_files = list(screenshots_dir.glob("*.png"))
        
    if not png_files:
        st.info("No failure screenshots discovered in screenshots/ directory.")
    else:
        # User filters
        search_test = st.text_input("Filter by Test Name:", "").strip()
        selected_date = st.date_input("Filter by File Modification Date:", value=None)
        
        matching_files = []
        for file in png_files:
            file_name = file.name
            
            # Filter by name
            if search_test and search_test.lower() not in file_name.lower():
                continue
                
            # Filter by date
            if selected_date:
                mtime_date = datetime.fromtimestamp(file.stat().st_mtime).date()
                if mtime_date != selected_date:
                    continue
                    
            matching_files.append(file)
            
        if not matching_files:
            st.info("No screenshots match the specified filters.")
        else:
            file_options = {f.name: f for f in matching_files}
            selected_filename = st.selectbox("Select screenshot to view:", list(file_options.keys()))
            
            if selected_filename:
                file_path = file_options[selected_filename]
                try:
                    img = Image.open(file_path)
                    st.markdown(f"**File Path:** `{file_path}`")
                    st.image(img, caption=selected_filename, use_container_width=True)
                except Exception as img_err:
                    st.error(f"Could not load image: {str(img_err)}")

# ==============================================================================
# PAGE 5 — Execution Logs
# ==============================================================================
elif page == "Execution Logs":
    st.markdown("<div class='custom-title'>Log Telemetry Log Book</div>", unsafe_allow_html=True)
    st.write("Read and query log file output lines generated during test cycles.")
    
    logs_dir = ROOT_DIR / "logs"
    log_files = []
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        
    if not log_files:
        st.info("No log files (.log) discovered in the logs/ directory.")
    else:
        log_filenames = [lf.name for lf in log_files]
        selected_log = st.selectbox("Select log file to inspect:", log_filenames)
        
        if selected_log:
            file_path = logs_dir / selected_log
            search_query = st.text_input("🔍 Search / Filter log lines:", "").strip()
            
            try:
                with open(file_path, "r", encoding="utf-8") as lf:
                    lines = lf.readlines()
                    
                filtered_lines = []
                for line in lines:
                    if search_query and search_query.lower() not in line.lower():
                        continue
                    filtered_lines.append(line.strip())
                    
                if not filtered_lines:
                    st.info("No log lines match the search criteria.")
                else:
                    # Render color coded box for lines
                    log_html = ""
                    for line in filtered_lines:
                        # Determine color representation
                        if "STATUS=PASS" in line:
                            # Healed checks
                            if "ERROR=None" not in line and "ERROR=" in line:
                                color = "#f59e0b"  # Healed
                            else:
                                color = "#10b981"  # Direct Pass
                        elif "STATUS=FAIL" in line or "STATUS=FAILED" in line:
                            color = "#ef4444"
                        elif "HEALED" in line:
                            color = "#f59e0b"
                        else:
                            color = "#94a3b8"
                            
                        log_html += f"<div style='font-family: monospace; padding: 4px; border-bottom: 1px solid rgba(255,255,255,0.05); color:{color};'>{line}</div>"
                        
                    st.markdown(
                        f"<div style='background-color:#0f172a; padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); max-height: 500px; overflow-y: auto;'>{log_html}</div>",
                        unsafe_allow_html=True
                    )
            except Exception as read_err:
                st.error(f"Could not read log file: {str(read_err)}")

# ==============================================================================
# PAGE 6 — AI Recommendations
# ==============================================================================
elif page == "AI Recommendations":
    st.markdown("<div class='custom-title'>AI Recommendation Analytics</div>", unsafe_allow_html=True)
    st.write("Analysis of AI confidence metrics, suggestion frequencies, and best-performing repairs.")
    
    failures_df = db_manager.get_all_failures()
    fixes_df = db_manager.get_all_learned_fixes()
    
    has_data = False
    
    # Extract confidence scores from ai_suggestion in failures
    confidences = []
    dates = []
    
    if not failures_df.empty:
        for idx, row in failures_df.iterrows():
            sugg = row.get("ai_suggestion") or ""
            match = re.search(r"Confidence:\s*(\d+)%", sugg)
            if match:
                confidences.append(int(match.group(1)))
                dates.append(row.get("timestamp"))
                
    if confidences:
        has_data = True
        conf_df = pd.DataFrame({"Timestamp": dates, "Confidence": confidences})
        conf_df["Timestamp"] = pd.to_datetime(conf_df["Timestamp"])
        conf_df = conf_df.sort_values("Timestamp")
        
        # Line chart of confidence scores over time
        fig_conf = px.line(
            conf_df,
            x="Timestamp",
            y="Confidence",
            title="AI Suggestion Confidence Trend",
            markers=True,
            color_discrete_sequence=["#c084fc"],
            template="plotly_dark"
        )
        st.plotly_chart(fig_conf, use_container_width=True)
        
    # Suggested replacement frequencies
    if not fixes_df.empty:
        has_data = True
        rep_counts = fixes_df["new_locator"].value_counts().reset_index()
        rep_counts.columns = ["Replacement Locator", "Frequency"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_rep = px.bar(
                rep_counts.head(10),
                x="Frequency",
                y="Replacement Locator",
                orientation="h",
                title="Top Replacement Locators by Frequency",
                color="Frequency",
                color_continuous_scale="Viridis",
                template="plotly_dark"
            )
            st.plotly_chart(fig_rep, use_container_width=True)
            
        with col2:
            st.markdown("### Top 10 Fixes Ranked by Confidence")
            ranked_fixes = fixes_df.sort_values(by="confidence", ascending=False).head(10)
            st.dataframe(ranked_fixes[["old_locator", "new_locator", "confidence", "usage_count"]], use_container_width=True)
            
    if not has_data:
        st.info("No AI recommendations recorded in the failures or learned fixes tables yet.")

# ==============================================================================
# PAGE 7 — Prompt Documentation
# ==============================================================================
elif page == "Prompt Documentation":
    st.markdown("<div class='custom-title'>AI Prompt Engineering Log</div>", unsafe_allow_html=True)
    st.write("Review prompt structure and configurations used to prompt the AI agents in this framework.")
    
    prompt_file_path = ROOT_DIR / "prompts_used.md"
    
    if prompt_file_path.exists():
        try:
            with open(prompt_file_path, "r", encoding="utf-8") as pf:
                md_content = pf.read()
            st.markdown(md_content)
        except Exception as read_err:
            st.error(f"Error loading prompt file: {str(read_err)}")
    else:
        st.info("The file prompts_used.md could not be located in the project root directory.")

# ==============================================================================
# PAGE 8 — Performance Metrics
# ==============================================================================
elif page == "Performance Metrics":
    st.markdown("<div class='custom-title'>Performance Metrics & Speed Trend</div>", unsafe_allow_html=True)
    st.write("Execution timing analysis, historical averages, slow test detections, and healing overhead.")
    
    perf_df = db_manager.get_all_performance()
    history_df = db_manager.get_all_test_history()
    
    if perf_df.empty:
        st.info("No performance telemetry entries found in the SQLite database performance table.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            # Sort by ID to plot chronologically
            perf_chron = perf_df.sort_values(by="id")
            fig_exec = px.line(
                perf_chron,
                x="id",
                y="execution_time",
                title="Test Execution Duration per Run",
                markers=True,
                labels={"id": "Execution ID", "execution_time": "Time (seconds)"},
                color_discrete_sequence=["#10b981"],
                template="plotly_dark"
            )
            st.plotly_chart(fig_exec, use_container_width=True)
            
        with col2:
            # Avg time trend over last 20 runs
            last_20 = perf_chron.tail(20)
            fig_avg = px.line(
                last_20,
                x="id",
                y="avg_time",
                title="Rolling Average Trend (Last 20 Runs)",
                markers=True,
                labels={"id": "Execution ID", "avg_time": "Rolling Avg (seconds)"},
                color_discrete_sequence=["#f59e0b"],
                template="plotly_dark"
            )
            st.plotly_chart(fig_avg, use_container_width=True)
            
        # Highlight slow tests
        st.markdown("### Slow Test Run Detection Details")
        st.write("Runs flagged where execution duration exceeded twice the rolling historical average.")
        
        slow_runs = []
        for idx, row in perf_df.iterrows():
            exec_time = row["execution_time"]
            avg = row["avg_time"]
            # Flag if run took > 2x average
            if avg and exec_time > 2 * avg:
                slow_runs.append(row)
                
        if slow_runs:
            slow_df = pd.DataFrame(slow_runs)
            
            # Apply styling to dataframe
            def color_slow(val):
                return "background-color: rgba(239, 68, 68, 0.2); color: #ef4444;"
                
            st.dataframe(slow_df.style.map(color_slow, subset=["execution_time"]), use_container_width=True)
        else:
            st.info("No execution runs exceeded the anomalies threshold (>2x average execution speed).")
            
        # Side-by-side comparison: before heal time vs after heal time
        if not history_df.empty:
            st.markdown("### Direct Passes vs Healed Run Durations")
            avg_direct = history_df[history_df["healed"] == 0]["execution_time"].mean()
            avg_healed = history_df[history_df["healed"] == 1]["execution_time"].mean()
            
            # Replace NaN with 0.0
            avg_direct = round(avg_direct, 4) if pd.notna(avg_direct) else 0.0
            avg_healed = round(avg_healed, 4) if pd.notna(avg_healed) else 0.0
            
            comparison_data = pd.DataFrame({
                "Execution Mode": ["Direct Pass (No Healing)", "Healed Execution (AI Recovery overhead)"],
                "Average Time (Seconds)": [avg_direct, avg_healed]
            })
            
            fig_comp = px.bar(
                comparison_data,
                x="Execution Mode",
                y="Average Time (Seconds)",
                color="Execution Mode",
                title="Average Execution Timings Comparison",
                color_discrete_map={"Direct Pass (No Healing)": "#10b981", "Healed Execution (AI Recovery overhead)": "#f59e0b"},
                template="plotly_dark"
            )
            st.plotly_chart(fig_comp, use_container_width=True)

# ==============================================================================
# PAGE 9 — Healing Leaderboard
# ==============================================================================
elif page == "Healing Leaderboard":
    st.markdown("<div class='custom-title'>Healing Efficiency & Leaderboard</div>", unsafe_allow_html=True)
    st.write("Performance analysis evaluating recovery success, top fixes, and aggregate manual triage hours saved.")
    
    history_df = db_manager.get_all_test_history()
    fixes_df = db_manager.get_all_learned_fixes()
    
    if history_df.empty:
        st.info("No test history recorded. Execution metrics are not available.")
    else:
        # Leaderboard: tests ranked by number of times healed
        st.markdown("### Tests Ranked by Recovery Events")
        healed_tests = history_df[history_df["healed"] == 1]
        
        if healed_tests.empty:
            st.info("No healing events have occurred yet.")
        else:
            rankings = healed_tests.groupby("test_name").size().reset_index(name="Healing Events")
            rankings = rankings.sort_values(by="Healing Events", ascending=False)
            st.dataframe(rankings, use_container_width=True)
            
        col1, col2 = st.columns(2)
        
        with col1:
            # Top AI fix: row with highest confidence in learned_fixes
            st.markdown("### Highest Confidence AI Fix")
            if fixes_df.empty:
                st.info("No learned fixes.")
            else:
                top_fix = fixes_df.sort_values(by="confidence", ascending=False).head(1)
                st.dataframe(top_fix[["old_locator", "new_locator", "confidence", "usage_count"]], use_container_width=True)
                
            # Healing efficiency score gauge
            total_runs = len(history_df)
            healed_runs = len(healed_tests)
            
            efficiency_score = (healed_runs / total_runs) * 100 if total_runs > 0 else 0.0
            efficiency_score = round(efficiency_score, 2)
            
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=efficiency_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Healing Success Efficiency (%)"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#818cf8"},
                    'steps': [
                        {'range': [0, 50], 'color': "#1e293b"},
                        {'range': [50, 80], 'color': "#334155"},
                        {'range': [80, 100], 'color': "#475569"}
                    ],
                }
            ))
            fig_gauge.update_layout(template='plotly_dark', height=250)
            st.plotly_chart(fig_gauge, use_container_width=True)
            
        with col2:
            st.markdown("### ROI: Manual Triage Time Saved")
            st.write(
                "Each test healed automatically saves developers from manual locator triage, script rewrites, and pull request cycles. "
                "We calculate time savings assuming a conservative manual recovery time of **5 minutes** per locator failure."
            )
            
            total_saved_minutes = healed_runs * 5
            hours = total_saved_minutes // 60
            minutes = total_saved_minutes % 60
            
            st.markdown(
                f"<div class='metric-card' style='margin-top:20px; padding:30px; border-color:#10b981;'>"
                f"<div class='metric-lbl' style='color:#34d399;'>Total Developer Hours Saved</div>"
                f"<div class='metric-val' style='color:#10b981; font-size:48px;'>{hours}h {minutes}m</div>"
                f"<div style='font-size:14px; margin-top:10px; color:#94a3b8;'>({total_saved_minutes} minutes saved across {healed_runs} healing events)</div>"
                f"</div>",
                unsafe_allow_html=True
            )

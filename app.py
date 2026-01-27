import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import tempfile
import os

# ================= 1. CONFIGURATION =================
st.set_page_config(
    page_title="AI Health Architect",
    layout="wide",
    page_icon="🥗"
)

# ================= 2. API HANDLING =================
api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    pass

if not api_key:
    with st.sidebar:
        st.warning("⚠️ Running Locally")
        api_key = st.text_input("Enter Gemini API Key:", type="password", help="Enter your Google Gemini API Key here.")

if api_key:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"API Error: {e}")

# ================= 3. AI ENGINE =================
def generate_plan_internal(age, bmi, activity, food, goal, budget, cuisine):
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    Act as a professional Nutritionist. Return ONLY valid JSON.
    PROFILE: Age: {age}, BMI: {bmi}, Activity: {activity}, Diet: {food}, Goal: {goal}
    CONSTRAINTS: Budget: {budget}, Cuisine: {cuisine}.
    JSON Structure:
    {{
      "overview": ["tip1", "tip2", "tip3"],
      "macros": {{ "protein_grams": 0, "carbs_grams": 0, "fats_grams": 0, "daily_calories": 0 }},
      "who_analysis": {{ "score": "8/10", "feedback": "Brief WHO analysis." }},
      "diet": [ {{"day":"Mon", "breakfast":"...", "lunch":"...", "dinner":"..."}}, ... ],
      "workout": [ {{"day":"Mon", "workout":"...", "duration":"...", "intensity":"..."}}, ... ]
    }}
    """
    try:
        res = model.generate_content(prompt)
        clean_json = res.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        return {"error": str(e)}

# ================= 4. SESSION STATE =================
if "page" not in st.session_state: st.session_state.page = "Home"
if "plans" not in st.session_state: st.session_state.plans = []
if "current_plan" not in st.session_state: st.session_state.current_plan = None
if "view" not in st.session_state: st.session_state.view = "Current Plan"
if "progress" not in st.session_state: st.session_state.progress = 0 

# ================= 5. ULTRA-PREMIUM CSS (FIXED) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    .stApp { background: radial-gradient(circle at 50% 10%, #2e1065 0%, #0f172a 40%, #000000 100%); color: #e2e8f0; }

    /* GLASS CARDS */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin-bottom: 24px;
    }

    /* --- NAVIGATION BUTTONS (3D GLASS EFFECT) --- */
    /* Targets: Home Button AND Menu Trigger Button */
    div.stButton > button, 
    div[data-testid="stPopover"] > div > button {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        padding: 12px 20px !important;
        border-radius: 50px !important; /* Pill Shape */
        font-weight: 600 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
    }

    /* Hover Effect (Neon Glow) */
    div.stButton > button:hover, 
    div[data-testid="stPopover"] > div > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.6) !important;
        border-color: #6366f1 !important;
        background: rgba(99, 102, 241, 0.1) !important;
    }
    
    /* Force Menu Icon Color to White */
    div[data-testid="stPopover"] > div > button * {
        color: white !important;
        fill: white !important;
    }

    /* --- DROPDOWN MENU INTERIOR STYLING --- */
    /* 1. Force the Dropdown Container to be Dark Blue */
    div[data-testid="stPopoverBody"] {
        background-color: #6366f1 !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        color: #6366f1 !important;
    }

    /* 2. Style the Buttons INSIDE the Menu (Glass Effect) */
    div[data-testid="stPopoverBody"] button {
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: #6366f1 !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 50px !important; /* Pill Shape inside menu */
        margin-bottom: 8px !important;
        padding: 10px 15px !important;
        transition: all 0.2s ease !important;
    }

    /* 3. Hover Effect for Menu Items */
    div[data-testid="stPopoverBody"] button:hover {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: #6366f1 !important;
        box-shadow: 0 0 10px rgba(99, 102, 241, 0.4) !important;
        transform: translateX(5px) !important;
    }

    /* 4. Fix Icons inside Menu Items */
    div[data-testid="stPopoverBody"] button * {
        color: #6366f1 !important;
        fill: #6366f1 !important;
    }

    /* --- COOL ANIMATED TITLE --- */
    @keyframes shine {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #a855f7, #3b82f6, #14b8a6, #a855f7);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        animation: shine 5s infinite linear;
        margin-bottom: 5px;
    }
    .hero-subtitle { text-align: center; color: #94a3b8; margin-bottom: 25px; letter-spacing: 1px; }

    /* --- 3D NEON METRIC CARDS --- */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 20px 40px rgba(0,0,0,0.4);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .metric-card.cal:hover { box-shadow: 0 0 30px rgba(16, 185, 129, 0.3); border-color: #10b981; }
    .metric-card.pro:hover { box-shadow: 0 0 30px rgba(168, 85, 247, 0.3); border-color: #a855f7; }
    .metric-card.carb:hover { box-shadow: 0 0 30px rgba(59, 130, 246, 0.3); border-color: #3b82f6; }
    .metric-card.fat:hover { box-shadow: 0 0 30px rgba(249, 115, 22, 0.3); border-color: #f97316; }
    
    .metric-value { font-size: 2.2rem; font-weight: 800; margin: 5px 0; }
    .metric-label { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; }

    /* Download Button */
    [data-testid="stDownloadButton"] > button {
        background: linear-gradient(90deg, #10b981 0%, #3b82f6 100%) !important;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.4) !important;
        color: white !important;
    }

    /* Tables & Progress */
    .styled-table th { background: linear-gradient(90deg, #6366f1, #8b5cf6); color: white; padding: 12px; }
    .styled-table td { border-bottom: 1px solid rgba(255,255,255,0.1); padding: 10px; color: #e2e8f0; }
    .stProgress > div > div > div > div { background-image: linear-gradient(90deg, #6366f1, #38bdf8); }
</style>
""", unsafe_allow_html=True)

# ================= 6. HEADER & NAVIGATION =================
st.markdown('<div class="hero-title">AI Health Architect</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">INTELLIGENT • ADAPTIVE • PERSONALIZED</div>', unsafe_allow_html=True)

# NAVIGATION BAR
nav_c1, nav_c2, nav_space = st.columns([1, 1, 8])

with nav_c1:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "Home"
        st.session_state.view = "Current Plan"
        st.rerun()

with nav_c2:
    with st.popover("☰ Menu", use_container_width=True):
        if st.button("📝 Generator", use_container_width=True): 
            st.session_state.page = "Home"; st.session_state.view = "Current Plan"; st.rerun()
        if st.button("📜 History", use_container_width=True): 
            st.session_state.page = "Home"; st.session_state.view = "History"; st.rerun()
        if st.button("ℹ️ About", use_container_width=True): st.session_state.page = "About"; st.rerun()
        if st.button("📩 Contact", use_container_width=True): st.session_state.page = "Contact"; st.rerun()

st.divider()

# ================= 7. PAGE LOGIC =================

# --- PAGE: HOME ---
if st.session_state.page == "Home":
    
    if st.session_state.view == "Current Plan":
        
        left_col, right_col = st.columns([3.5, 8.5], gap="large")
        
        # SIDEBAR
        with left_col:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("⚙️ Biometrics")
            age = st.number_input("Age", 10, 100, 22)
            c_h, c_w = st.columns(2)
            with c_h: height = st.number_input("Height (cm)", 120, 220, 170)
            with c_w: weight = st.number_input("Weight (kg)", 30, 200, 65)
            
            bmi = round(weight / ((height / 100) ** 2), 2)
            st.info(f"BMI: {bmi}")
            
            st.subheader("🥗 Preferences")
            activity = st.selectbox("Activity", ["Sedentary", "Moderate", "Active"])
            food = st.selectbox("Diet Type", ["Vegetarian", "Non-Vegetarian", "Vegan"])
            
            # Problem Statement Inputs
            budget = st.select_slider("Budget Constraint", options=["Student (Low Cost)", "Standard", "Premium"])
            cuisine = st.text_input("Cuisine/Region", "South Indian", help="E.g., North Indian, Continental")
            
            goal = st.selectbox("Goal", ["Weight Loss", "Muscle Gain", "Maintenance"])
            st.markdown("---")
            generate = st.button("✨ Generate Plan", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Weekly Progress
            with st.expander("📅 Weekly Progress Check-in"):
                week_num = st.slider("Weeks Completed", 0, 12, st.session_state.progress)
                if st.button("Update Progress"):
                    st.session_state.progress = week_num
                    st.success("Updated!")
                    st.rerun()

        # MAIN OUTPUT
        with right_col:
            if st.session_state.progress > 0:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown(f"**Journey Progress: Week {st.session_state.progress}/12**")
                st.progress(st.session_state.progress / 12)
                st.markdown('</div>', unsafe_allow_html=True)

            if generate:
                if not api_key:
                    st.warning("👈 Please enter API Key in sidebar.")
                else:
                    with st.spinner("🧠 AI is analyzing budget, cuisine & nutrition..."):
                        data = generate_plan_internal(age, bmi, activity, food, goal, budget, cuisine)
                        if "error" in data:
                            if "429" in data["error"]: st.error("⚠️ Quota Exceeded. Try again tomorrow.")
                            else: st.error(f"Error: {data['error']}")
                        else:
                            st.session_state.current_plan = {"date": datetime.now().strftime("%Y-%m-%d"), "data": data}
                            st.session_state.plans.append(st.session_state.current_plan)

            if st.session_state.current_plan:
                plan = st.session_state.current_plan["data"]
                m = plan["macros"]
                
                # === 3D METRIC CARDS ===
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(f"""<div class="metric-card cal"><div style="font-size:2rem;">🔥</div><div class="metric-value" style="color:#10b981;">{m['daily_calories']}</div><div class="metric-label">Calories</div></div>""", unsafe_allow_html=True)
                with c2: st.markdown(f"""<div class="metric-card pro"><div style="font-size:2rem;">🥩</div><div class="metric-value" style="color:#a855f7;">{m['protein_grams']}g</div><div class="metric-label">Protein</div></div>""", unsafe_allow_html=True)
                with c3: st.markdown(f"""<div class="metric-card carb"><div style="font-size:2rem;">🍞</div><div class="metric-value" style="color:#3b82f6;">{m['carbs_grams']}g</div><div class="metric-label">Carbs</div></div>""", unsafe_allow_html=True)
                with c4: st.markdown(f"""<div class="metric-card fat"><div style="font-size:2rem;">🥑</div><div class="metric-value" style="color:#f97316;">{m['fats_grams']}g</div><div class="metric-label">Fats</div></div>""", unsafe_allow_html=True)
                
                st.write("")
                
                # Charts & Score
                c_chart, c_score = st.columns([1.5, 1])
                with c_chart:
                    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                    df = pd.DataFrame({"Macro":["P","C","F"], "Value":[m['protein_grams'], m['carbs_grams'], m['fats_grams']]})
                    fig = px.pie(df, values="Value", names="Macro", hole=0.6, color_discrete_sequence=["#a855f7", "#3b82f6", "#f97316"])
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", height=220, margin=dict(t=0,b=0,l=0,r=0))
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                with c_score:
                    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                    who = plan['who_analysis']
                    color = "#22c55e" if "8" in who['score'] or "9" in who['score'] else "#eab308"
                    st.markdown(f"<h1 style='color:{color}; text-align:center;'>{who['score']}</h1>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align:center;'>WHO Compliance Score</p>", unsafe_allow_html=True)
                    st.write(who['feedback'])
                    st.markdown('</div>', unsafe_allow_html=True)

                # Tables
                st.subheader("🗓️ Weekly Schedule")
                t1, t2 = st.tabs(["🍽️ Diet Plan", "🏋️ Workout Plan"])
                with t1:
                    rows = "".join([f"<tr><td><strong>{r['day']}</strong></td><td>{r['breakfast']}</td><td>{r['lunch']}</td><td>{r['dinner']}</td></tr>" for r in plan["diet"]])
                    st.markdown(f"<table class='styled-table'><thead><tr><th>Day</th><th>Breakfast</th><th>Lunch</th><th>Dinner</th></tr></thead><tbody>{rows}</tbody></table>", unsafe_allow_html=True)
                with t2:
                    rows = "".join([f"<tr><td><strong>{r['day']}</strong></td><td>{r['workout']}</td><td>{r['duration']}</td><td>{r['intensity']}</td></tr>" for r in plan["workout"]])
                    st.markdown(f"<table class='styled-table'><thead><tr><th>Day</th><th>Focus</th><th>Duration</th><th>Intensity</th></tr></thead><tbody>{rows}</tbody></table>", unsafe_allow_html=True)

                # PDF Logic
                def safe_text(text): return text.encode("latin-1", "ignore").decode("latin-1")
                class PDF(FPDF):
                    def header(self):
                        self.set_font('Arial', 'B', 20); self.set_text_color(99, 102, 241)
                        self.cell(0, 10, 'AI Health Architect', 0, 1, 'C'); self.ln(5)
                
                def generate_pdf(plan):
                    pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", "I", 10); pdf.set_text_color(100)
                    pdf.cell(0, 10, f"Generated: {plan['date']}", ln=True, align='C'); pdf.ln(5)
                    pdf.set_font("Arial", "B", 12); pdf.set_text_color(0); pdf.cell(0, 8, "Overview", ln=True)
                    pdf.set_font("Arial", size=10)
                    for p in plan["data"]["overview"]: pdf.multi_cell(0, 6, safe_text(f"- {p}"))
                    pdf.ln(5)
                    
                    def get_max_height(pdf, col_widths, data_row):
                        max_h = 0
                        for i, text in enumerate(data_row):
                            lines = pdf.multi_cell(col_widths[i], 5, safe_text(text), split_only=True)
                            h = len(lines) * 5
                            if h > max_h: max_h = h
                        return max(max_h, 8)

                    # Diet Table
                    pdf.set_font("Arial", "B", 14); pdf.set_text_color(99, 102, 241); pdf.cell(0, 10, "Diet Schedule", ln=True)
                    headers, widths = ["Day", "Breakfast", "Lunch", "Dinner"], [25, 55, 55, 55]
                    pdf.set_font("Arial", "B", 10); pdf.set_text_color(255); pdf.set_fill_color(99, 102, 241)
                    for i, h in enumerate(headers): pdf.cell(widths[i], 8, h, 1, 0, 'C', 1)
                    pdf.ln(); pdf.set_text_color(0); pdf.set_font("Arial", size=9)
                    for r in plan["data"]["diet"]:
                        row_data = [r['day'], r['breakfast'], r['lunch'], r['dinner']]
                        h = get_max_height(pdf, widths, row_data)
                        if pdf.get_y() + h > 270: pdf.add_page(); pdf.ln()
                        x, y = pdf.get_x(), pdf.get_y()
                        for i, text in enumerate(row_data):
                            pdf.set_xy(x + sum(widths[:i]), y); pdf.multi_cell(widths[i], 5, safe_text(text), border=1)
                            pdf.set_xy(x + sum(widths[:i]), y); pdf.rect(x + sum(widths[:i]), y, widths[i], h)
                        pdf.set_y(y + h)
                    
                    # Workout Table
                    pdf.ln(10)
                    if pdf.get_y() > 250: pdf.add_page()
                    pdf.set_font("Arial", "B", 14); pdf.set_text_color(99, 102, 241); pdf.cell(0, 10, "Workout Schedule", ln=True)
                    w_headers, w_widths = ["Day", "Focus Area", "Duration", "Intensity"], [25, 80, 40, 45]
                    pdf.set_font("Arial", "B", 10); pdf.set_text_color(255); pdf.set_fill_color(99, 102, 241)
                    for i, h in enumerate(w_headers): pdf.cell(w_widths[i], 8, h, 1, 0, 'C', 1)
                    pdf.ln(); pdf.set_text_color(0); pdf.set_font("Arial", size=9)
                    for r in plan["data"]["workout"]:
                        row_data = [r['day'], r['workout'], r['duration'], r['intensity']]
                        h = get_max_height(pdf, w_widths, row_data)
                        if pdf.get_y() + h > 270: pdf.add_page(); pdf.ln()
                        x, y = pdf.get_x(), pdf.get_y()
                        for i, text in enumerate(row_data):
                            pdf.set_xy(x + sum(w_widths[:i]), y); pdf.multi_cell(w_widths[i], 5, safe_text(text), border=1)
                            pdf.set_xy(x + sum(w_widths[:i]), y); pdf.rect(x + sum(w_widths[:i]), y, w_widths[i], h)
                        pdf.set_y(y + h)

                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    pdf.output(tmp.name)
                    return tmp.name

                st.write("")
                pdf_file = generate_pdf(st.session_state.current_plan)
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Full PDF Report",
                        data=f,
                        file_name="My_AI_Health_Plan.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                if not generate:
                    st.markdown("""
                    <div style='text-align: center; padding: 50px; opacity: 0.6;'>
                        <h1>👈</h1>
                        <h3>Start Your Journey</h3>
                        <p>Enter your biometrics in the sidebar to generate a WHO-compliant plan.</p>
                    </div>
                    """, unsafe_allow_html=True)

    elif st.session_state.view == "History":
        st.subheader("📜 Past Plans")
        if not st.session_state.plans:
            st.info("No history found. Generate a plan to get started!")
        for p in reversed(st.session_state.plans):
            with st.expander(f"Plan created on {p['date']}"):
                st.json(p['data']['macros'])

# --- PAGE: ABOUT ---
elif st.session_state.page == "About":
    st.markdown('<div class="hero-title">About the Project</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="glass-card">
            <h3>🎯 Problem Statement</h3>
            <p>University students often face health issues due to poor nutrition and lack of guidance. 
            Existing solutions are either expensive or generic. This project aims to democratize 
            personalized health planning using Generative AI, specifically addressing 
            <strong>Budget Constraints</strong> and <strong>Cultural Food Habits</strong>.</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="glass-card">
            <h3>🚀 Tech Stack</h3>
            <p><strong>Python</strong> (Logic), <strong>Streamlit</strong> (UI), 
            <strong>Google Gemini</strong> (AI), <strong>Plotly</strong> (Charts).</p>
        </div>
        """, unsafe_allow_html=True)

# --- PAGE: CONTACT ---
elif st.session_state.page == "Contact":
    st.markdown('<div class="hero-title">Contact Us</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="glass-card" style="text-align:center;">
        <h3>👨‍💻 Developer Information</h3>
        <p><strong>Name:</strong> ADITYA ENGINEERING COLLEGE</p>
        <p><strong>Email:</strong> manibhushan354@gmail.com</p>
        <hr>
        <p><em>EDUNET AND IBM INTERNSHIP Project 2026</em></p>
    </div>
    """, unsafe_allow_html=True)
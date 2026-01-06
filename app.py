# -*- coding: utf-8 -*-
import os
import google.generativeai as genai
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
app = Flask(__name__)

# Configure Gemini API
api_key = os.environ.get("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

# --- SIMON SYSTEM PROMPT (PROFESSIONAL EDITION) ---
def get_simon_prompt(user_raw_input):
    return f"""
    You are **Simon**, the AI-Assisted Home Valuation Expert for AgentCoachAI.com.
    
    ====================
    OBJECTIVE
    ====================
    Create a HIGHLY PROFESSIONAL, clean, and visually structured Valuation Report.
    The output must look like a premium document, not just a chat message.

    ====================
    INPUTS
    ====================
    {user_raw_input}

    ====================
    CRITICAL INSTRUCTIONS FOR DATA
    ====================
    1. **NO "N/A" TABLES:** Since you cannot browse live Zillow/Redfin links in real-time, DO NOT fill the table with "N/A" or broken links. Instead, use your internal market knowledge to generate **"Estimated Algo Ranges"** for these platforms based on the comps you find. Mark them as "Est."
    2. **COMPS:** Identify 3 specific, realistic comparable sales based on the location. If exact recent sales are hidden, estimate high-confidence proxies based on neighborhood data.
    3. **MATH:** Ensure the "Adjusted Midpoint" is mathematically consistent with your weighted adjustments.

    ====================
    REQUIRED MARKDOWN OUTPUT FORMAT
    ====================
    (Do not add introductory chat text. Start directly with the report).

    # 📑 AI-Assisted Valuation Report
    
    **Property:** {{Address}}
    **Date:** {{Current Date}}
    **Prepared For:** {{Agent Name}}

    ---

    ## 1. Subject Property Analysis
    | Feature | Details |
    | :--- | :--- |
    | **Configuration** | {{Beds}} Bed / {{Baths}} Bath |
    | **Size** | {{SqFt}} Sq.Ft. (Approx) |
    | **Key Updates** | {{List key upgrades concisely}} |
    | **Location Factor** | {{List location benefits}} |

    ## 2. Market Data Synthesis
    *Aggregated estimation from major valuation models based on comps.*

    | Algorithm Source | Estimated Range | Status |
    | :--- | :--- | :--- |
    | **Zillow (Est)** | ${{Low}}k – ${{High}}k | Market Avg |
    | **Redfin (Est)** | ${{Low}}k – ${{High}}k | Algorithm |
    | **Realtor (Est)** | ${{Low}}k – ${{High}}k | Conservative |
    
    > **Note:** Above figures are simulated estimates based on comparable market data.

    ## 3. Comparable Sales (The "Comps")
    *Recent activity supporting this valuation:*

    * **📍 {{Comp 1 Address}}**
        * {{Beds}}/{{Baths}} • {{SqFt}} sqft
        * **Sold: ${{Price}}** ({{Date}})
        * *Analysis:* {{Compare to subject, e.g., "Inferior kitchen, similar size"}}

    * **📍 {{Comp 2 Address}}**
        * {{Beds}}/{{Baths}} • {{SqFt}} sqft
        * **Sold: ${{Price}}** ({{Date}})
        * *Analysis:* {{Compare to subject}}

    * **📍 {{Comp 3 Address}}**
        * {{Beds}}/{{Baths}} • {{SqFt}} sqft
        * **Sold: ${{Price}}** ({{Date}})
        * *Analysis:* {{Compare to subject}}

    ---

    ## 4. Simon's Professional Opinion
    
    ### 📊 Valuation Matrix
    | Metric | Value |
    | :--- | :--- |
    | **Raw Comp Average** | **${{Raw_Midpoint}}** |
    | **Net Adjustments** | **{{+/- Percentage}}%** ({{Reason for adjustment}}) |
    | **Final Adjusted Midpoint** | **${{Final_Midpoint}}** |

    ### ✅ Recommended Pricing Strategy
    **Fair Market Value Range:**
    # 💰 ${{Low_Range}} – ${{High_Range}}

    **Agent Strategy:**
    {{Provide specific strategic advice. E.g., "To capture the weekend traffic, list at $264,900. If speed is priority..."}}

    **Confidence Score:**
    {{Low/Medium/High}} — {{One sentence rationale}}.

    ---
    *Prepared by Simon — AgentCoachAI.com*
    *Agent: {{Agent Name}} • {{Phone}}*

    <small>DISCLAIMER: This is an AI-assisted estimate using publicly available data. It is not a formal appraisal. Verify all data independently.</small>
    """

# --- FRONTEND (PROFESSIONAL DARK UI) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simon - AgentCoachAI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0F172A;
            --chat-bg: #1E293B;
            --report-bg: #FFFFFF; /* Report is white for professionalism */
            --text-color: #F1F5F9;
            --report-text: #334155;
            --accent-color: #38BDF8;
            --input-bg: #334155;
        }
        body { font-family: 'Inter', sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; display: flex; flex-direction: column; height: 100vh; }
        
        .header { padding: 15px; text-align: center; border-bottom: 1px solid #334155; background-color: #020617; }
        .header h1 { margin: 0; font-size: 1.2rem; color: white; display: flex; align-items: center; justify-content: center; gap: 8px; }
        
        .chat-container { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 20px; max-width: 800px; margin: 0 auto; width: 100%; box-sizing: border-box; }
        
        .message { display: flex; gap: 15px; max-width: 100%; animation: fadeIn 0.3s ease-in; }
        
        .bot-avatar { 
            width: 35px; height: 35px; 
            background: linear-gradient(135deg, #0EA5E9, #2563EB); 
            border-radius: 6px; 
            display: flex; align-items: center; justify-content: center; 
            font-weight: bold; color: white; flex-shrink: 0; font-size: 14px;
        }
        
        /* ESTILO DEL REPORTE (Look Documento) */
        .message-content { 
            background-color: var(--chat-bg); 
            padding: 15px; 
            border-radius: 12px; 
            line-height: 1.6; 
            white-space: pre-wrap; 
            width: 100%;
        }
        
        /* Cuando es el reporte de Simon, cambiamos el estilo para que parezca "Papel" o "Tarjeta Profesional" */
        .bot-message .message-content {
            background-color: #F8FAFC; /* White-ish paper */
            color: #1E293B; /* Dark text for readability */
            border: 1px solid #CBD5E1;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        /* Markdown Styling inside the Report */
        h1 { color: #0F172A; font-size: 1.4em; border-bottom: 2px solid #0EA5E9; padding-bottom: 10px; margin-top: 0; }
        h2 { color: #2563EB; font-size: 1.1em; margin-top: 25px; margin-bottom: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        h3 { color: #475569; font-size: 1em; margin-top: 15px; }
        
        /* Tables Professional Style */
        table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 0.9em; background: white; border-radius: 4px; overflow: hidden; }
        th { background-color: #E2E8F0; color: #334155; font-weight: 600; text-transform: uppercase; font-size: 0.8em; padding: 10px; border-bottom: 2px solid #CBD5E1; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #E2E8F0; color: #334155; }
        tr:last-child td { border-bottom: none; }
        
        blockquote { border-left: 4px solid #38BDF8; margin: 10px 0; padding-left: 15px; color: #64748B; font-style: italic; background: #F0F9FF; padding: 10px; border-radius: 4px; }
        small { color: #94A3B8; display: block; margin-top: 20px; font-size: 0.75em; text-align: center; }

        /* Input Area */
        .input-area { padding: 20px; background-color: var(--bg-color); border-top: 1px solid #334155; }
        .input-form { max-width: 800px; margin: 0 auto; position: relative; display: flex; }
        textarea { width: 100%; background-color: var(--input-bg); border: 1px solid #475569; border-radius: 12px; color: white; padding: 15px 50px 15px 20px; resize: none; height: 60px; outline: none; font-family: inherit; }
        textarea:focus { border-color: var(--accent-color); }
        .send-btn { position: absolute; right: 15px; top: 50%; transform: translateY(-50%); background: #38BDF8; border: none; color: #0F172A; width: 35px; height: 35px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
        .send-btn:hover { background: #0EA5E9; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Simon Valuation Expert</h1>
        <span>Powered by Agent Coach AI</span>
    </div>

    <div class="chat-container">
        <div class="message" style="flex-direction: row;">
            <div class="bot-avatar">S</div>
            <div class="message-content" style="background-color: #1E293B; color: #F1F5F9; border: none;">
                <strong>I am here to help you generate a professional, weighted home valuation report.</strong><br>
                Please paste the property details below.<br><br>
                1. <strong>Full Property Address</strong> (Required)
2. <strong>Beds / Baths / Sq Ft</strong>
3. <strong>Condition & Upgrades</strong> (e.g., new roof 2024, remodeled kitchen)
4. <strong>Special Features</strong> (e.g., cul-de-sac, views)
5. <strong>Agent Name + Phone</strong> (Required for signature)
                I will generate a professional <strong>Agent-Ready Report</strong>.
            </div>
        </div>

        {% if error %}
        <div style="background: #EF4444; color: white; padding: 10px; border-radius: 8px; text-align: center;">{{ error }}</div>
        {% endif %}

        {% if generated_text %}
        <div class="message bot-message">
            <div class="bot-avatar">S</div>
            <div class="message-content">{{ generated_text }}</div>
        </div>
        {% endif %}
    </div>

    <div class="input-area">
        <form class="input-form" method="POST" action="/">
            <textarea name="user_input" placeholder="Paste property & agent details here..." required></textarea>
            <button type="submit" class="send-btn">➤</button>
        </form>
    </div>

    <script>
        const chatContainer = document.querySelector('.chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;
        document.querySelector('textarea').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.form.submit();
            }
        });
    </script>
</body>
</html>
""" 

# --- ROUTES ---
@app.route("/", methods=["GET", "POST"])
def home():
    generated_text = ""
    error_message = ""
    
    if request.method == "POST":
        if not api_key:
            error_message = "Error: GOOGLE_API_KEY missing."
        else:
            try:
                user_input_block = request.form.get("user_input")
                # Using Gemini 2.0 Flash Exp for speed and logic
                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(get_simon_prompt(user_input_block))
                generated_text = response.text
            except Exception as e:
                error_message = f"Error: {str(e)}"

    return render_template_string(HTML_TEMPLATE, generated_text=generated_text, error=error_message)

if __name__ == "__main__":
    app.run(debug=True)


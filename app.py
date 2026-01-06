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

# --- SIMON SYSTEM PROMPT ---
def get_simon_prompt(user_raw_input):
    return f"""
    You are **Simon**, the AI-Assisted Home Valuation expert for AgentCoachAI.com.
    You are trained with 30+ years of broker insight.

    ====================
    YOUR MISSION
    ====================
    Collect inputs, apply professional weighting (seasonality, upgrades, velocity, size), and output a clean, agent-ready value range.

    ====================
    INPUTS PROVIDED BY USER:
    ====================
    {user_raw_input}

    ====================
    CRITICAL INSTRUCTIONS
    ====================
    1. **INTAKE CHECK:** If the user has NOT provided the "Full Property Address" OR the "Agent Name", do NOT generate a valuation. Instead, politely ask for the missing information.
    2. **NO BROWSING:** Since you cannot browse the live web in real-time in this environment, use your internal knowledge base to estimate comparable values and market conditions based on the address and specs provided. If specific platform data (Zillow/Redfin) is not accessible, make a highly educated estimate based on the property's location data you possess or mark as "N/A" if completely unknown.
    3. **TONE:** Professional, concise, plain-English. No hype.
    4. **COMPLIANCE:** strict Fair Housing compliance.
    5. **OUTPUT LANGUAGE:** ENGLISH ONLY.

    ====================
    WEIGHTED LOGIC TO APPLY
    ====================
    A) Seasonality: Nov-Feb (-1% to -3%), Mar-Jun (+2% to +4%), Jul-Aug (-1% to -2%), Sep-Oct (+1% to +2%). Warm states (FL, AZ, NV, TX) are neutral in winter.
    B) Upgrades: Major system <=3yrs (+1-2% each), Kitchen/Bath reno (+2-3%), Cosmetic (+0.5-1%). Max cap +5%.
    C) Velocity: <=10 DOM (+2-4%), 31-60 DOM (-1%), >=61 DOM (-3%).
    D) Size: If larger than comps, emphasize value. If smaller, -1% to -2%.
    E) TOTAL CAP: Combine A-D but cap total adjustment at +/- 7% from raw midpoint.

    ====================
    REQUIRED OUTPUT FORMAT
    ====================
    (Use these headers exactly)

    # AI-Assisted Home Valuation — Simon (AgentCoachAI.com)

    **Subject Property**
    • Address: {{address}}
    • Beds/Baths/Sq Ft: {{value}}
    • Notable Upgrades/Condition: {{bullets}}
    • Special Features/Location Notes: {{bullets}}

    ## Snapshot of Online Estimates
    | Source | Estimate | Link |
    |-------|----------|------|
    | Zillow | $X | [View] |
    | Redfin | $X | [View] |
    | Realtor.com | $X | [View] |
    | Homes.com | $X | [View] |
    | Trulia | $X | [View] |

    **Synthesis**
    • Raw Multi-Site Range: **$L_raw – $H_raw**
    • Raw Midpoint: **$M_raw**
    • Weighted Adjustment Applied (cap ±7%): **{{+/-X%}}**
    • Adjusted Fair-Market Range: **$L_adj – $H_adj**
    • Adjusted Midpoint: **$M_adj**
    • Widest Source Gap & Note: {{text}}

    ## Nearby Recent Comps (most relevant)
    • {{Comp 1}} — {{details}} — Closed {{date}}; **$price**; DOM {{#}}
    • {{Comp 2}} ...
    • {{Comp 3}} ...

    **Market Notes (micro-area)**
    • Trend: {{text}}
    • Typical DOM: {{text}}
    • PPSF context: {{text}}

    ## AI-Assisted Value Opinion (Non-Appraisal)
    Based on the sources above... the likely fair-market range for **{{address}}** is:
    **$L_adj – $H_adj**, with a working midpoint of **$M_adj**.
    Key drivers: {{bullets}}

    ## Pricing Strategy (agent-ready)
    • {{Strategy based on DOM}}

    ### Confidence Meter
    **{{Low / Medium / High}}** — {{rationale}}

    —
    **Prepared by Simon — AI-Assisted Home Valuation (AgentCoachAI.com)**
    **Agent:** {{Agent Name}} • {{Phone}} {{Website}}

    **Disclaimer (always include):**
    This AI-assisted home value opinion is a data-informed estimate based on publicly available information and nearby sales. It is **not** a formal appraisal and should not be used for lending decisions. For definitive valuation, consult a licensed appraiser. All information deemed reliable but not guaranteed.
    """

# --- FRONTEND (DARK CHAT UI - SIMON THEME) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simon - AgentCoachAI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0F172A; /* Dark Slate Blue background */
            --chat-bg: #1E293B; /* Slightly lighter slate */
            --text-color: #F1F5F9;
            --accent-color: #38BDF8; /* Sky Blue for Simon (Trust/Tech) */
            --input-bg: #334155;
            --user-msg-bg: #2563EB; /* Blue for user messages */
        }
        body { font-family: 'Inter', sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; display: flex; flex-direction: column; height: 100vh; }
        
        .header { padding: 20px; text-align: center; border-bottom: 1px solid #334155; background-color: #0F172A; }
        .header h1 { margin: 0; font-size: 1.5rem; display: flex; align-items: center; justify-content: center; gap: 10px; color: white; }
        .header span { font-size: 0.85rem; color: #94A3B8; display: block; margin-top: 5px; letter-spacing: 0.5px; }

        .chat-container { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 20px; max-width: 900px; margin: 0 auto; width: 100%; box-sizing: border-box; }
        
        .message { display: flex; gap: 15px; max-width: 90%; animation: fadeIn 0.3s ease-in; }
        
        /* Simon Avatar */
        .bot-avatar { 
            width: 40px; height: 40px; 
            background: linear-gradient(135deg, #38BDF8, #0284C7); 
            border-radius: 8px; /* Square-ish for professional look */
            display: flex; align-items: center; justify-content: center; 
            font-weight: bold; color: white; flex-shrink: 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .message-content { background-color: var(--chat-bg); padding: 15px 20px; border-radius: 12px; line-height: 1.6; white-space: pre-wrap; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); }
        .bot-message .message-content { border-top-left-radius: 2px; border-left: 3px solid var(--accent-color); }
        
        /* Tables in Markdown */
        table { border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 0.9em; }
        th, td { border: 1px solid #475569; padding: 8px 12px; text-align: left; }
        th { background-color: #334155; color: var(--accent-color); }

        .input-area { padding: 20px; background-color: var(--bg-color); border-top: 1px solid #334155; }
        .input-form { max-width: 900px; margin: 0 auto; position: relative; display: flex; }
        textarea { width: 100%; background-color: var(--input-bg); border: 1px solid #475569; border-radius: 12px; color: white; padding: 15px 50px 15px 20px; resize: none; height: 80px; font-family: inherit; outline: none; transition: border 0.2s; }
        textarea:focus { border-color: var(--accent-color); }
        textarea::placeholder { color: #94A3B8; }
        
        .send-btn { position: absolute; right: 15px; top: 50%; transform: translateY(-50%); background: #38BDF8; border: none; color: #0F172A; width: 35px; height: 35px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; transition: background 0.2s; }
        .send-btn:hover { background: #0EA5E9; }

        .error-box { background-color: #EF4444; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-weight: bold; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        
        /* Markdown Headers in Chat */
        h1, h2, h3 { color: var(--accent-color); margin-top: 20px; margin-bottom: 10px; }
        strong { color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Simon — AI Valuation Expert</h1>
        <span>AgentCoachAI.com • 30+ Years Insight</span>
    </div>

    <div class="chat-container">
        <div class="message bot-message">
            <div class="bot-avatar">S</div>
            <div class="message-content">Hello, I'm <strong>Simon</strong>. I am here to help you generate a professional, weighted home valuation report.

To begin, please provide the following <strong>5 items</strong>:

1. <strong>Full Property Address</strong> (Required)
2. <strong>Beds / Baths / Sq Ft</strong>
3. <strong>Condition & Upgrades</strong> (e.g., new roof 2024, remodeled kitchen)
4. <strong>Special Features</strong> (e.g., cul-de-sac, views)
5. <strong>Agent Name + Phone</strong> (Required for signature)

Paste the details below, and I will research comps and calculate the adjustments.</div>
        </div>

        {% if error %}
        <div class="error-box">⚠️ {{ error }}</div>
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
            <textarea name="user_input" placeholder="Example: 123 Main St, Miami FL. 3/2, 1800sqft. New AC 2023. Agent: Carlos 555-0199..." required></textarea>
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
            error_message = "Error: GOOGLE_API_KEY missing in Railway variables."
        else:
            try:
                user_input_block = request.form.get("user_input")
                
                # Using Gemini 2.0 Flash Experimental
                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                
                response = model.generate_content(get_simon_prompt(user_input_block))
                generated_text = response.text
                
            except Exception as e:
                error_message = f"Error generating report: {str(e)}"

    return render_template_string(HTML_TEMPLATE, generated_text=generated_text, error=error_message)

if __name__ == "__main__":
    app.run(debug=True)
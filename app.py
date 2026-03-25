# -*- coding: utf-8 -*-
import os
import tempfile
import google.generativeai as genai
from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import markdown 

# --- CONFIGURATION ---
load_dotenv()
app = Flask(__name__)

# Configure Gemini API
api_key = os.environ.get("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

# --- STRATEGIST SYSTEM PROMPT ---
def get_strategist_prompt(user_raw_input, current_date):
    return f"""
    You are a high-performance real estate pricing strategist.

    Your job is to generate:
    - Accurate CMA price ranges
    - Clear pricing strategies
    - Seller communication (email, text, script)

    You must behave like an experienced listing agent who has priced hundreds of homes.
    
    CURRENT DATE: {current_date}

    CORE RULES (NON-NEGOTIABLE)
    - NEVER use external browsing or live searches
    - NEVER wait or “think” for long operations
    - ALWAYS respond immediately using ONLY user-provided data
    - If data is missing → STOP and ask clearly
    - If comps are weak → SAY IT directly

    FAIL-SAFE PROTOCOL
    If required data is missing:
    - No comps: Say "I can’t generate a reliable CMA without comps. Please paste at least 3 comparable properties or upload a document."
    - Incomplete comps: Say "The comps provided are not detailed enough. I need price, square footage, and status (sold/active/pending)."
    - Missing property details: Ask ONLY for the missing pieces (do not restart the process)

    7-QUESTION FLOW (MANDATORY)
    Ask these EXACT questions before generating the CMA if the user hasn't provided the info:
    1. ADDRESS: "What is the full property address?"
    2. PROPERTY BASICS: "Confirm: beds, baths, approximate square footage, and year built."
    3. COMPS (REQUIRED): "Paste or upload 3–6 comparable properties (MLS or Market Analysis Export)."
    4. CONDITION SCORE: "On a scale of 1–10, how does this home compare in condition to others nearby?"
    5. UPGRADES: "Any major upgrades? (roof, HVAC, kitchen, bathrooms, flooring, etc.)"
    6. NEGATIVE FACTORS: "Any issues? (repairs needed, outdated, location issues, hoarder condition, etc.)"
    7. SELLER STRATEGY: "What’s the goal: sell fast, maximize price, or balanced?"

    PROCESSING RULES
    Once answers are provided (either in text or via the uploaded document):
    STEP 1: PARSE COMPS
    - Extract: Price, Square footage, Status (sold / active / pending)
    - Ignore unclear data. Do NOT stall.
    
    STEP 2: ANALYZE
    - Calculate price per square foot
    - Identify strongest 3–5 comps
    - Ignore outliers
    
    STEP 3: APPLY ADJUSTMENTS
    Adjust based on:
    - Condition (1–10): Higher than comps → increase value | Lower → decrease value
    - Upgrades: New roof: +$5K–$15K | HVAC: +$5K–$10K | Renovated kitchen: +$10K–$25K | Full renovation: +$25K+
    - Negatives: Outdated: -$10K–$30K | Repairs: -$20K–$75K+ | Hoarder condition: -$25K–$100K+
    *Adjust proportionally to price range.*
    
    STEP 4: MARKET POSITION
    - Active listings = competition
    - Sold = proof of value
    - Pending = direction
    
    STEP 5: PRICE STRATEGY
    - Apply: Sell fast → slightly below market | Max price → upper range | Balanced → middle

    OUTPUT (MANDATORY FORMAT)
    
    FINAL VALUE
    Say EXACTLY: "This home is estimated to be worth between $X and $Y."
    Range must be: Tight whenever possible (Typically $10K–$25K spread).

    PRICING LOGIC
    Explain briefly: Comp positioning, Condition impact, Market competition.

    STRATEGY
    Explain outcome: If priced at low end, Mid range, High end.

    SELLER EMAIL
    Short, confident, data-backed.

    TEXT MESSAGE
    1–2 lines to prompt a call.

    PHONE SCRIPT
    Confident closing tone.

    SPEED RULES
    - No long essays
    - No fluff
    - No delays
    - One complete response

    DEMO MODE BEHAVIOR
    - If input is messy → extract what you can and proceed
    - If unsure → say “Based on the data provided…”
    - NEVER freeze
    - NEVER say “searching” or “checking”

    FINAL PRINCIPLE
    Speed + Clarity + Confidence = Listings Won

    ====================
    USER TEXT INPUT
    ====================
    {user_raw_input}
    
    Note: If a document was provided, it is attached to this prompt. Please analyze its contents alongside the user text input.
    """

# --- FRONTEND (PROFESSIONAL DARK UI) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simon - Real Estate Strategist</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0F172A;
            --chat-bg: #1E293B;
            --text-color: #F1F5F9;
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
        
        .message-content { background-color: var(--chat-bg); padding: 15px; border-radius: 12px; line-height: 1.6; width: 100%; }
        
        .bot-message .message-content {
            background-color: #F8FAFC; color: #1E293B; border: 1px solid #CBD5E1; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .message-content h1 { color: #0F172A; font-size: 1.5em; border-bottom: 2px solid #0EA5E9; padding-bottom: 10px; margin-top: 0; }
        .message-content h2 { color: #2563EB; font-size: 1.2em; margin-top: 25px; margin-bottom: 10px; font-weight: 700; text-transform: uppercase; }
        .message-content h3 { color: #475569; font-size: 1.1em; margin-top: 15px; }
        .message-content p { margin-bottom: 10px; }
        .message-content ul { padding-left: 20px; }
        .message-content li { margin-bottom: 5px; }
        .message-content strong { color: #000; font-weight: 700; }
        
        .message-content table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 0.9em; background: white; border-radius: 4px; overflow: hidden; }
        .message-content th { background-color: #E2E8F0; color: #334155; font-weight: 600; text-transform: uppercase; font-size: 0.8em; padding: 10px; border-bottom: 2px solid #CBD5E1; text-align: left; }
        .message-content td { padding: 10px; border-bottom: 1px solid #E2E8F0; color: #334155; }
        .message-content tr:last-child td { border-bottom: none; }
        
        .message-content blockquote { border-left: 4px solid #38BDF8; margin: 10px 0; padding-left: 15px; color: #64748B; font-style: italic; background: #F0F9FF; padding: 10px; border-radius: 4px; }

        /* Input Area with File Upload */
        .input-area { padding: 20px; background-color: var(--bg-color); border-top: 1px solid #334155; }
        .input-form { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 10px; }
        
        .textarea-container { position: relative; display: flex; width: 100%; }
        textarea { width: 100%; background-color: var(--input-bg); border: 1px solid #475569; border-radius: 12px; color: white; padding: 15px 50px 15px 20px; resize: none; height: 60px; outline: none; font-family: inherit; }
        textarea:focus { border-color: var(--accent-color); }
        .send-btn { position: absolute; right: 15px; top: 50%; transform: translateY(-50%); background: #38BDF8; border: none; color: #0F172A; width: 35px; height: 35px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s; font-weight: bold;}
        .send-btn:hover { background: #0EA5E9; }

        .file-upload-container { display: flex; align-items: center; gap: 10px; font-size: 0.9em; color: #94A3B8; }
        .file-input { display: none; }
        .file-label { background: #334155; padding: 8px 15px; border-radius: 6px; cursor: pointer; transition: background 0.2s; border: 1px solid #475569; display: inline-flex; align-items: center; gap: 5px; }
        .file-label:hover { background: #475569; color: white; }
        #file-name { font-style: italic; }

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
                I am Simon, your real estate pricing strategist.<br>
                Please paste the property details below, or <strong>upload a document (PDF, CSV, TXT)</strong> containing the MLS export or comps data.
            </div>
        </div>

        {% if error %}
        <div style="background: #EF4444; color: white; padding: 10px; border-radius: 8px; text-align: center;">{{ error }}</div>
        {% endif %}

        {% if generated_html %}
        <div class="message bot-message">
            <div class="bot-avatar">S</div>
            <div class="message-content">{{ generated_html | safe }}</div>
        </div>
        {% endif %}
    </div>

    <div class="input-area">
        <form class="input-form" method="POST" action="/" enctype="multipart/form-data">
            
            <div class="file-upload-container">
                <input type="file" name="document" id="file-upload" class="file-input" accept=".pdf,.csv,.txt,.xlsx,.xls" />
                <label for="file-upload" class="file-label">📎 Attach Comps File</label>
                <span id="file-name">No file chosen</span>
            </div>

            <div class="textarea-container">
                <textarea name="user_input" placeholder="Type property details or context for the attached file..."></textarea>
                <button type="submit" class="send-btn">➤</button>
            </div>
        </form>
    </div>

    <script>
        // Scroll al fondo del chat
        const chatContainer = document.querySelector('.chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Enviar con Enter
        document.querySelector('textarea').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.form.submit();
            }
        });

        // Mostrar el nombre del archivo seleccionado
        document.getElementById('file-upload').addEventListener('change', function(e) {
            const fileName = e.target.files[0] ? e.target.files[0].name : "No file chosen";
            document.getElementById('file-name').textContent = fileName;
        });
    </script>
</body>
</html>
""" 

# --- ROUTES ---
@app.route("/", methods=["GET", "POST"])
def home():
    generated_html = "" 
    error_message = ""
    
    if request.method == "POST":
        if not api_key:
            error_message = "Error: GOOGLE_API_KEY missing. Please add it to your environment variables."
        else:
            try:
                user_input_block = request.form.get("user_input", "")
                uploaded_file = request.files.get("document")
                
                # 1. Obtener fecha actual
                now = datetime.now()
                current_date_str = now.strftime("%B %d, %Y")
                
                # 2. Preparar el contenido a enviar a Gemini
                prompt_text = get_strategist_prompt(user_input_block, current_date_str)
                contents_to_send = [prompt_text]
                
                gemini_uploaded_file = None
                temp_file_path = None

                # 3. Procesar el archivo si el usuario subió uno
                if uploaded_file and uploaded_file.filename != '':
                    # Guardar el archivo en una ubicación temporal segura
                    ext = os.path.splitext(uploaded_file.filename)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                        uploaded_file.save(temp_file.name)
                        temp_file_path = temp_file.name
                    
                    # Subir el archivo a la API de Gemini
                    gemini_uploaded_file = genai.upload_file(temp_file_path)
                    contents_to_send.append(gemini_uploaded_file)

                # 4. Generar respuesta con Gemini (le pasamos el array que puede contener texto + archivo)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(contents_to_send)
                raw_markdown = response.text
                
                # 5. Convertir Markdown a HTML
                generated_html = markdown.markdown(raw_markdown, extensions=['tables'])

            except Exception as e:
                error_message = f"Error processing request: {str(e)}"
            
            finally:
                # 6. LIMPIEZA CRÍTICA: Borrar archivos temporales para no agotar espacio/cuota
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                
                if gemini_uploaded_file:
                    try:
                        genai.delete_file(gemini_uploaded_file.name)
                    except Exception as cleanup_error:
                        print(f"Warning: Failed to delete file from Gemini API: {cleanup_error}")

    return render_template_string(HTML_TEMPLATE, generated_html=generated_html, error=error_message)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

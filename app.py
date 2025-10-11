import streamlit as st # type: ignore
from huggingface_hub import InferenceClient # type: ignore
from pymongo import MongoClient # type: ignore
import hashlib
from datetime import datetime
import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore

# --- Configuration ---
st.set_page_config(
    page_title="Fake News Detector",
    page_icon="📰",
    layout="wide"
)

# --- Custom CSS for Modern UI ---
st.markdown("""
<style>
    .main {
        background-color: black;
    }
    
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 0 0 25px 25px;
        margin-bottom: 2rem;
        margin-top: -4rem;
        color: white;
        text-align: center;
    }
    
    .custom-card {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .custom-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    
    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        margin: 0.5rem;
    }
    
    .credibility-score {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .warning-score {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .danger-score {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    .stTextInput input, .stTextArea textarea {
        border-radius: 15px;
        border: 2px solid #e0e0e0;
        padding: 1rem;
        font-size: 1rem;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    .analysis-section {
        border-left: 4px solid #667eea;
        padding-left: 1.5rem;
        margin: 1.5rem 0;
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
    }
    
    .verdict-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .reliable {
        background: #4CAF50;
        color: white;
    }
    
    .misleading {
        background: #ff9800;
        color: white;
    }
    
    .false {
        background: #f44336;
        color: white;
    }
    
    .opinion {
        background: #9c27b0;
        color: white;
    }
 
</style>
""", unsafe_allow_html=True)


# --- User Authentication and Data Management ---
# --- MongoDB Connection ---
@st.cache_resource
def get_mongo_client():
    """Establishes a connection to MongoDB and returns the collection object."""
    try:
        MONGO_URI = st.secrets["MONGO_URI"]
        DB_NAME = st.secrets["DB_NAME"]
        COLLECTION_NAME = st.secrets["COLLECTION_NAME"]
        client = MongoClient(MONGO_URI)
        return client[DB_NAME][COLLECTION_NAME]
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        st.stop()

users_collection = get_mongo_client()

def hash_password(password):
    """Hashes a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verifies a provided password against a stored hash."""
    return stored_password == hash_password(provided_password)

def add_to_history(username, interaction_type, user_input, ai_response):
    """Adds a generated study interaction to the user's history."""
    history_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": interaction_type,
        "input": user_input,
        "response": ai_response
    }
    users_collection.update_one({"_id": username}, {"$push": {"history": {"$each": [history_entry], "$position": 0}}})

# Hugging Face token (securely stored in Streamlit secrets)
# Make sure to add HF_TOKEN to your Streamlit secrets
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
except FileNotFoundError:
    st.error("Streamlit secrets file not found. Please create a .streamlit/secrets.toml file with your HF_TOKEN.")
    st.stop()

client = InferenceClient("meta-llama/Meta-Llama-3-8B-Instruct", token=HF_TOKEN)

# --- System Prompt for News Analysis ---
NEWS_ANALYSIS_PROMPT = """You are an expert AI fact-checker and news analyst. Your goal is to help students identify misinformation by providing a critical analysis of news articles.
When given an article's text, you must perform the following tasks and structure your response in Markdown exactly as follows:

**Credibility Score:** [Provide a score from 1-10, where 1 is 'Highly Unreliable' and 10 is 'Highly Reliable'.]
**Verdict:** [A one-sentence verdict: 'Likely Reliable', 'Potentially Misleading', 'Likely False', or 'Opinion/Satire'.]

**Analysis:**
*   **Tone & Bias:** [Analyze the language. Is it neutral or emotionally charged? Does it favor a particular viewpoint?]
*   **Sources & Evidence:** [Does the article cite sources? Are they reputable? Does it provide evidence for its claims?]
*   **Fact-Checking:** [Based on your knowledge, identify any potential factual inaccuracies or unverified claims.]
*   **Red Flags:** [Mention any common misinformation tactics used, like sensationalism, logical fallacies, or lack of author information.]

**Neutral Summary:**
[Provide a concise, unbiased summary of the article's main points, stripped of any emotional or biased language.]
"""

# --- AI & UI Component Functions ---

@st.cache_data(show_spinner=False) # Cache the AI response to avoid re-generating on widget interactions
def generate_ai_response(system_prompt, user_prompt):
    """
    Generates a response from the LLaMA model based on a system and user prompt.
    """
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {"role": "user", "content": user_prompt},
    ]

    response_text = ""
    try:
        # Use chat_completion for conversational models like Llama-3
        for chunk in client.chat_completion(messages, max_tokens=2048, temperature=0.7, stream=True):
            # Add a check to ensure the choices list is not empty before accessing it
            if chunk.choices and chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
    except Exception as e:
        st.error(f"An error occurred while communicating with the AI model: {e}", icon="💔")
        return "Sorry, I couldn't generate a response at this moment. Please try again later."

    return response_text.strip()

def get_article_text(url):
    """Fetches and extracts text content from a URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if len(text) < 200: # Check if we got meaningful content
            return None, "Could not extract enough meaningful text from the URL. The site might be heavily reliant on JavaScript or block scraping."
            
        return text, None
    except requests.exceptions.RequestException as e:
        return None, f"Failed to fetch the article. Error: {e}"
    except Exception as e:
        return None, f"An error occurred while parsing the article: {e}"

def display_modern_header():
    """Display modern header with gradient"""
    st.markdown("""
    <div class="header-container">
        <h1 style="margin:0; font-size: 3rem; font-weight: 700;">📰 AI Fact Checker</h1>
        <p style="margin:0; font-size: 1.3rem; opacity: 0.9; margin-top: 0.5rem;">
        Detect misinformation and verify news credibility with AI-powered analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

def display_features():
    """Display feature cards"""
    st.markdown("### 🔍 What We Analyze")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>🎯 Credibility Score</h3>
            <p>1-10 reliability rating</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>🔎 Bias Detection</h3>
            <p>Identify political & emotional bias</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>📊 Fact Checking</h3>
            <p>Verify claims & sources</p>
        </div>
        """, unsafe_allow_html=True)

def display_modern_auth():
    """Display modern authentication in sidebar"""
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color: #667eea; margin: 0;">Fact Checker</h2>
            <p style="color: #666; margin: 0;">AI News Analysis</p>
        </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.logged_in:
            tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
            
            with tab1:
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pass")
                
                if st.button("Login", use_container_width=True):
                    if username and password:
                        user_data = users_collection.find_one({"_id": username})
                        if user_data and verify_password(user_data["password"], password):
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    else:
                        st.warning("Please enter username and password")
            
            with tab2:
                username = st.text_input("Username", key="reg_user")
                password = st.text_input("Password", type="password", key="reg_pass")
                confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
                
                if st.button("Register", use_container_width=True):
                    if username and password:
                        if password == confirm_password:
                            if users_collection.find_one({"_id": username}):
                                st.error("Username already exists")
                            else:
                                users_collection.insert_one({
                                    "_id": username,
                                    "password": hash_password(password),
                                    "history": []
                                })
                                st.success("Registration successful! Please login.")
                        else:
                            st.error("Passwords do not match")
                    else:
                        st.warning("Please fill all fields")
        else:
            st.markdown(f"""
            <div class="custom-card">
                <h4 style="color: #667eea; margin: 0;">Welcome back!</h4>
                <p style="margin: 0.5rem 0; color: #666;">{st.session_state.username}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.rerun()

def display_analysis_form():
    """Display the modern analysis form"""
    st.markdown("""
    <div class="custom-card">
        <h2 style="color: #333; margin-bottom: 1.5rem; text-align: center;">🔍 Analyze News Article</h2>
    """, unsafe_allow_html=True)
    
    input_method = st.radio(
        "Choose input method:",
        ["🔗 URL", "📝 Paste Text"],
        horizontal=True,
        label_visibility="collapsed"
    )

    article_text = ""
    source_identifier = ""

    if input_method == "🔗 URL":
        url = st.text_input(
            "**Enter News Article URL**",
            placeholder="https://example.com/news-article",
            help="Paste the full URL of the news article you want to analyze"
        )
        if url:
            with st.spinner("🌐 Fetching article content..."):
                article_text, error = get_article_text(url)
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.success("✅ Article content fetched successfully!")
                    source_identifier = url
    else:  # Paste Text
        article_text = st.text_area(
            "**Paste Article Text**",
            height=250,
            placeholder="Paste the full text of the news article here...",
            help="Copy and paste the complete article text for analysis"
        )
        source_identifier = "Pasted Text"
    
    st.markdown("</div>", unsafe_allow_html=True)
    return article_text, source_identifier

def display_analysis_results(analysis, source_identifier):
    """Display the analysis results in a modern layout"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; padding: 2rem; border-radius: 20px; text-align: center; margin: 2rem 0;">
        <h2 style="margin:0; color: white;">✅ Analysis Complete</h2>
        <p style="margin:0.5rem 0 0 0; opacity: 0.9;">Your news article has been analyzed</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Extract score and verdict for special formatting
    lines = analysis.split('\n')
    credibility_score = None
    verdict = None
    
    for i, line in enumerate(lines):
        if "Credibility Score:" in line:
            credibility_score = line.split(":")[1].strip()
        if "Verdict:" in line:
            verdict = line.split(":")[1].strip()
    
    # Display score and verdict prominently
    if credibility_score and verdict:
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                score_num = int(credibility_score.split('/')[0].strip())
                if score_num >= 7:
                    st.markdown(f"""
                    <div class="credibility-score">
                        <h3 style="margin:0; font-size: 2.5rem;">{credibility_score}</h3>
                        <p style="margin:0; opacity: 0.9;">Credibility Score</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif score_num >= 4:
                    st.markdown(f"""
                    <div class="warning-score">
                        <h3 style="margin:0; font-size: 2.5rem;">{credibility_score}</h3>
                        <p style="margin:0; opacity: 0.9;">Credibility Score</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="danger-score">
                        <h3 style="margin:0; font-size: 2.5rem;">{credibility_score}</h3>
                        <p style="margin:0; opacity: 0.9;">Credibility Score</p>
                    </div>
                    """, unsafe_allow_html=True)
            except:
                pass
        
        with col2:
            verdict_class = "reliable"
            if "Misleading" in verdict:
                verdict_class = "misleading"
            elif "False" in verdict:
                verdict_class = "false"
            elif "Opinion" in verdict or "Satire" in verdict:
                verdict_class = "opinion"
                
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem;">
                <h3 style="margin:0; color: #333;">Verdict</h3>
                <div class="verdict-badge {verdict_class}" style="font-size: 1.2rem;">
                    {verdict}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Display full analysis
    st.markdown("""
    <div class="custom-card">
        <h3 style="color: #333; margin-bottom: 1.5rem;">📊 Detailed Analysis</h3>
    """, unsafe_allow_html=True)
    st.markdown(analysis)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Add copy button for the analysis
    st.code(analysis, language="markdown")
    
    # Save to history
    add_to_history(st.session_state.username, "News Analysis", source_identifier, analysis)

def display_modern_history():
    """Display modern history view"""
    st.markdown("""
    <div class="custom-card">
        <h2 style="color: #333; text-align: center; margin-bottom: 2rem;">📚 Analysis History</h2>
    """, unsafe_allow_html=True)
    
    user_data = users_collection.find_one({"_id": st.session_state.username})
    user_history = user_data.get("history", []) if user_data else []

    if not user_history:
        st.markdown("""
        <div style="text-align: center; padding: 3rem;">
            <h3 style="color: #666;">No analyses yet</h3>
            <p>Your news analyses will appear here!</p>
            <div style="font-size: 4rem;">📰</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for i, entry in enumerate(user_history):
            with st.expander(f"📅 {entry['type']} from {entry['date']}", expanded=(i==0)):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.markdown("**Source:**")
                    st.info(entry['input'][:100] + '...' if len(entry['input']) > 100 else entry['input'])
                
                with col2:
                    st.markdown("**Analysis:**")
                    st.markdown(entry["response"])
    
    st.markdown("</div>", unsafe_allow_html=True)

# --- Main App Interface ---
display_modern_header()

# --- Authentication ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

display_modern_auth()

if not st.session_state.logged_in:
    # Welcome screen for non-logged in users
    st.markdown("""
    <div class="custom-card">
        <h2 style="text-align: center; color: #333; margin-bottom: 2rem;">Welcome to AI Fact Checker! 🛡️</h2>
        <p style="text-align: center; font-size: 1.2rem; color: #666; line-height: 1.6;">
        In today's digital age, misinformation spreads rapidly. Our AI-powered tool helps you 
        verify news credibility, detect bias, and identify fake news to make informed decisions.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    display_features()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); color: white; padding: 2rem; border-radius: 20px; text-align: center; margin: 2rem 0;">
        <p style="margin: 0; font-size: 1.2rem;">
        👈 <strong>Get Started:</strong> Please login or register in the sidebar to start analyzing news!
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- Main Application ---
if st.session_state.logged_in:
    # --- Main Application Tabs ---
    tab1, tab2 = st.tabs(["🔍 Analyze News", "📚 History"])

    with tab1:
        display_features()
        article_text, source_identifier = display_analysis_form()
        
        analyze_button = st.button(
            "🔬 Analyze Article", 
            use_container_width=True, 
            disabled=not article_text,
            type="primary"
        )
        
        if analyze_button and article_text:
            with st.spinner("🤖 AI is analyzing the article... This may take a moment."):
                user_prompt = f"Please analyze the following news article:\n\n---\n\n{article_text}"
                analysis = generate_ai_response(NEWS_ANALYSIS_PROMPT, user_prompt)
                display_analysis_results(analysis, source_identifier)
        elif not article_text:
            st.info("💡 **Tip:** Enter a URL or paste article text above to start analysis")

    with tab2:
        display_modern_history()


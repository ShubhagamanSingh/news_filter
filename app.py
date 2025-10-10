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

def display_history():
    """Renders the user's interaction history."""
    st.header("Your Analysis History")
    user_data = users_collection.find_one({"_id": st.session_state.username})
    user_history = user_data.get("history", []) if user_data else []

    if not user_history:
        st.info("You have no saved analyses yet. Analyze an article to see your history here!")
    else:
        for entry in user_history:
            expander_title = f"{entry['type']} from {entry['date']}"
            with st.expander(expander_title):
                st.write(f"**Interaction Type:** {entry['type']}")
                st.caption(f"**Source:** {entry['input']}")

                st.markdown("---")
                st.write("**AI Response:**")
                st.markdown(entry["response"])

# --- Main App Interface ---
st.title("📰 Fake News Detector for Students")
st.markdown("In an era of rapid information sharing, it's crucial to distinguish fact from fiction. This tool helps you analyze news articles for credibility, bias, and factual accuracy to combat misinformation.")

# --- Authentication UI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.sidebar.title("Login / Register")
    choice = st.sidebar.radio("Choose an action", ["Login", "Register"])

    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if choice == "Register":
        if st.sidebar.button("Register"):
            if username and password:
                # Check if user already exists
                if users_collection.find_one({"_id": username}):
                    st.sidebar.error("Username already exists.")
                else:
                    users_collection.insert_one({
                        "_id": username,
                        "password": hash_password(password),
                        "history": []
                    })
                    st.sidebar.success("Registration successful! Please log in.")
            else:
                st.sidebar.warning("Please enter a username and password.")

    if choice == "Login":
        if st.sidebar.button("Login"):
            if username and password:
                user_data = users_collection.find_one({"_id": username})
                if user_data and verify_password(user_data["password"], password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun() # Rerun the script to show the main app
                else:
                    st.sidebar.error("Invalid username or password.")
            else:
                st.sidebar.warning("Please enter your username and password.")

    st.info("Please log in or register to use the Fake News Detector. Open the sidebar by clicking the top-left icon.", icon="👈")

# --- Main Application ---
if st.session_state.logged_in:
    st.sidebar.title(f"Welcome, {st.session_state.username}! 👋")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    # --- Main Application Tabs ---
    analyzer_tab, history_tab = st.tabs(["🔍 Analyze News", "📜 History"])

    with analyzer_tab:
        st.header("Analyze an Article")
        input_method = st.radio("Choose input method:", ["URL", "Paste Text"], horizontal=True)

        article_text = ""
        source_identifier = ""

        if input_method == "URL":
            url = st.text_input("Enter the news article URL:", placeholder="https://example.com/news-article")
            if url:
                with st.spinner("Fetching article from URL..."):
                    article_text, error = get_article_text(url)
                    if error:
                        st.error(error)
                    else:
                        st.success("Article content fetched successfully!")
                        source_identifier = url
        else: # Paste Text
            article_text = st.text_area("Paste the article text here:", height=250)
            source_identifier = "Pasted Text"

        if st.button("🔬 Analyze Article", use_container_width=True, disabled=not article_text):
            with st.spinner("AI is analyzing the article... This may take a moment. 🧠"):
                user_prompt = f"Please analyze the following news article:\n\n---\n\n{article_text}"
                analysis = generate_ai_response(NEWS_ANALYSIS_PROMPT, user_prompt)

                st.markdown("---")
                st.subheader("✨ Analysis Complete")
                st.markdown(analysis)

                # Save to history
                add_to_history(st.session_state.username, "News Analysis", source_identifier, analysis)

                # Add a copy button for the analysis
                st.code(analysis, language="markdown")

        elif not article_text and input_method == "Paste Text":
             st.info("Please paste the article text above to be analyzed.")

    with history_tab:
        display_history()

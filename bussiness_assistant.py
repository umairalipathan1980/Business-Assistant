import streamlit as st
import anthropic
import os
import time
import json
import re
from datetime import datetime
import random
import uuid
import base64
from io import BytesIO
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

import base64
from io import BytesIO
import requests


# Get API keys from .env
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]

# Configure page
st.set_page_config(
    page_title="Future Proof Mentor",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling - enhanced based on example
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        gap: 0.75rem;
    }
    .chat-message.user {
        background-color: #e6f7ff;
    }
    .chat-message.assistant {
        background-color: #f0f2f5;
    }
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
    }
    .chat-message .message {
        flex: 1;
    }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        border-radius: 10px;
    }
    /* Button styling for equal dimensions */
    .stButton > button {
        border-radius: 10px;
        padding: 0.5rem 1rem;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        width: 100%; /* Full width buttons */
        height: 44px; /* Fixed height for all buttons */
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 5px;
        line-height: 1.2;
    }
    .stButton > button:hover {
        background-color: #45a049;
    }
    .model-buttons {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 15px;
    }
    .stSidebar {
        background-color: #f0f2f5;
        padding: 2rem 1rem;
    }
    .sidebar-title {
        text-align: center;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .css-18e3th9 {
        padding-top: 2rem;
    }
    .model-option {
        display: flex;
        align-items: center;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        cursor: pointer;
    }
    .model-option:hover {
        background-color: rgba(0,0,0,0.05);
    }
    .model-option.selected {
        background-color: rgba(76, 175, 80, 0.2);
        border-left: 3px solid #4CAF50;
    }
    .model-icon {
        width: 30px;
        height: 30px;
        margin-right: 10px;
    }
    .welcome-card {
        background-color: white;
        border-radius: 10px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .welcome-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    .welcome-icon {
        font-size: 2rem;
        margin-right: 1rem;
    }
    .followup-questions {
        margin-top: 1rem;
    }
    .followup-button {
        margin: 0.2rem 0;
        padding: 0.5rem;
        background-color: #f0f2f5;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        text-align: left;
        transition: background-color 0.3s;
        width: 100%;
        height: 44px;
    }
    .followup-button:hover {
        background-color: #e6f7ff;
    }
    .reference {
        color: blue;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gpt-4o"
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'chat_started' not in st.session_state:
    st.session_state.chat_started = False
if 'greeting_added' not in st.session_state:
    st.session_state.greeting_added = False
if 'followup_questions' not in st.session_state:
    st.session_state.followup_questions = []
if 'followup_key' not in st.session_state:
    st.session_state.followup_key = 0
if 'pending_followup' not in st.session_state:
    st.session_state.pending_followup = None
if 'last_assistant' not in st.session_state:
    st.session_state.last_assistant = None

# Future Proof Mentor system prompt
FUTURE_PROOF_MENTOR_PROMPT = """
As Future Proof Mentor, your role is to guide entrepreneurs through scenario building, strategic foresight, and adaptive planning. Your responses should be structured, practical, and applicable to different industries. You should:  

1. **Guide Entrepreneurs Through Scenario Planning:**  
   - Explain **scenario planning frameworks** such as **PESTLE, STEEP, Four Futures, or 2x2 Matrix**.  
   - Help users define **key uncertainties and driving forces** in their industry.  
   - Encourage thinking in **multiple possible futures** rather than just one prediction.  

2. **Identify Emerging Trends & Weak Signals:**  
   - Analyze **megatrends, technological shifts, regulatory changes, and economic shifts**.  
   - Help users find **weak signals** (subtle indicators of change) in their industry.  
   - Suggest reliable sources for tracking emerging trends.  

3. **Assess Risks & Opportunities in Each Scenario:**  
   - Provide structured **risk mapping and mitigation strategies**.  
   - Identify **opportunities for growth, innovation, and competitive advantage**.  
   - Help users create **early warning indicators** to monitor market shifts.  

4. **Assist in Backcasting & Strategic Decision-Making:**  
   - Help users **reverse-engineer their preferred future** and define key actions to achieve it.  
   - Offer **agile business strategies** for adapting to different possible futures.  
   - Suggest **resilient business models** suitable for uncertain environments.  

5. **Generate Scenario-Based "What If?" Questions:**  
   - Offer industry-agnostic **"What if?" prompts** to encourage forward-thinking.  
   - Challenge entrepreneurs to **consider extreme but plausible futures**.  

6. **Provide Real-World Examples & Case Studies:**  
   - Share examples of businesses that successfully adapted to **unexpected change**.  
   - Offer **sector-specific insights** when needed (tech, retail, healthcare, etc.).  

Tone & Style:
- Be **insightful, structured, and actionable**.  
- Encourage **strategic thinking** with a mix of **theoretical models and real-world applications**.  
- Keep it **industry-agnostic**, but provide **sector-specific insights** when relevant.

When greeting a user for the first time, ask: "To get started, what industry is your business in? What are the biggest changes--technological, economic, regulatory, or social--that could impact it in the next 5--10 years?"

Other important points:
- After generating the answer, offer user with more help and support by hinting potential follow up questions and further explanations. Tell user what you can offer/do after having a follow up question. Be interactive and supportive. Use simple and easy to understand terminologies.
- Make your answer well-formatted, with the inclusion of as many visual cues, icons, and other grapical elements (but no logs or URL of images) as possible. Consider creating tables, graphs, flowcharts, and other related elements to enhance the presentation of the answer. Be as explanatory as possible. 
- Answer questions only relevant to the contents of this prompt. For other questions, respond with "Sorry! I am not designed to answer this question".
"""

# Function to convert chat history to markdown format
def get_chat_history_markdown():
    """
    Convert the chat history to a markdown string format
    """
    markdown_text = "# Future Proof Mentor Chat History\n\n"
    markdown_text += f"Session ID: {st.session_state.session_id}\n"
    markdown_text += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    markdown_text += f"Model: {st.session_state.selected_model}\n\n"
    markdown_text += "---\n\n"
    
    for message in st.session_state.chat_history:
        timestamp = message.get("timestamp", "")
        if message["role"] == "user":
            markdown_text += f"## User ({timestamp})\n\n"
            markdown_text += f"{message['content']}\n\n"
        else:
            markdown_text += f"## Assistant ({timestamp})\n\n"
            markdown_text += f"{message['content']}\n\n"
        markdown_text += "---\n\n"
    
    return markdown_text

# Function to process user questions
def process_question(question):
    """
    Process a question (typed or follow-up):
      1. Append as a user message.
      2. Run the LLM and stream the assistant's response.
    """
    # 1) Add user question to the chat
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.chat_history.append({
        "role": "user", 
        "content": question, 
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Set chat as started
    st.session_state.chat_started = True
    
    # 2) Get AI response
    start_time = time.time()
    
    if st.session_state.selected_model == "gpt-4o":
        response = call_openai_api(st.session_state.messages)
    else:
        response = call_langchain_anthropic_api(st.session_state.messages)
    
    # 3) Add assistant response to chat
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": response, 
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # 4) Update follow-up tracking
    st.session_state.followup_key += 1
    
    # Store this as the latest assistant message for follow-up generation
    st.session_state.last_assistant = response

# Function to call OpenAI API using LangChain's ChatOpenAI
def call_openai_api(messages):
    try:
        # Initialize the LangChain OpenAI client
        chat = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model="gpt-4o",
            max_tokens = 8000,
            streaming=True
        )
        
        # Format messages for OpenAI including system prompt and full chat history
        formatted_messages = [{"role": "system", "content": FUTURE_PROOF_MENTOR_PROMPT}]
        
        # Add conversation history
        for msg in messages:
            formatted_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Set up placeholder for streaming
        placeholder = st.empty()
        collected_content = ""
        
        # Process streaming response
        for chunk in chat.stream(formatted_messages):
            if chunk.content:
                collected_content += chunk.content
                # Apply reference styling
                styled_response = re.sub(
                    r'\[(.*?)\]',
                    r'<span class="reference">[\1]</span>',
                    collected_content
                )
                placeholder.markdown(f"""
                <div class="chat-message assistant">
                    <div class="avatar">🔮</div>
                    <div class="message">{styled_response}</div>
                </div>
                """, unsafe_allow_html=True)
        
        return collected_content
    
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return "I'm sorry, there was an error processing your request. Please try again."

# Function to call Anthropic API using LangChain's ChatAnthropic (updated implementation)
def call_langchain_anthropic_api(messages):
    try:
        # Initialize the LangChain Anthropic client
        chat = ChatAnthropic(
            anthropic_api_key=ANTHROPIC_API_KEY,
            model="claude-3-7-sonnet-20250219",
            max_tokens = 8000
            )
        
        # Format messages for Anthropic
        formatted_messages = []
        
        # Add system message as first message
        formatted_messages.append({"role": "system", "content": FUTURE_PROOF_MENTOR_PROMPT})
        
        # Then add the conversation history
        for msg in messages:
            role = "human" if msg["role"] == "user" else "assistant"
            formatted_messages.append({"role": role, "content": msg["content"]})
        
        # Set up placeholder for streaming
        placeholder = st.empty()
        collected_content = ""
        
        # Process streaming response
        for chunk in chat.stream(formatted_messages):
            if hasattr(chunk, 'content') and chunk.content:
                collected_content += chunk.content
                # Apply reference styling
                styled_response = re.sub(
                    r'\[(.*?)\]',
                    r'<span class="reference">[\1]</span>',
                    collected_content
                )
                placeholder.markdown(f"""
                <div class="chat-message assistant">
                    <div class="avatar">🔮</div>
                    <div class="message">{styled_response}</div>
                </div>
                """, unsafe_allow_html=True)
        
        return collected_content
    
    except Exception as e:
        st.error(f"Error calling Anthropic API: {str(e)}")
        return "I'm sorry, there was an error processing your request. Please try again."

# Function to handle follow-up question selection
def handle_followup(question):
    st.session_state.pending_followup = question

# Sidebar
with st.sidebar:
    st.markdown("<h1 class='sidebar-title'>🔮 Future Proof Mentor</h1>", unsafe_allow_html=True)
    
    st.markdown("### Select AI Model")
    
    # Model buttons with consistent sizing
    st.markdown("<div class='model-buttons'>", unsafe_allow_html=True)
    
    # OpenAI GPT-4o option
    openai_selected = st.session_state.selected_model == "gpt-4o"
    if st.button(
        f"OpenAI GPT-4o", 
        key="openai-btn", 
        help="OpenAI's GPT-4o model - versatile, high performance AI",
        type="secondary" if not openai_selected else "primary",
        use_container_width=True):
        st.session_state.selected_model = "gpt-4o"
        st.rerun()

    # Anthropic Claude option
    claude_selected = st.session_state.selected_model == "claude-3.7-sonnet"
    if st.button(
        f"Anthropic Claude 3.7-sonnet", 
        key="claude-btn", 
        help="Anthropic's Claude 3.7 Sonnet - excellent for structured business planning",
        type="secondary" if not claude_selected else "primary",
        use_container_width=True):
        st.session_state.selected_model = "claude-3.7-sonnet"
        st.rerun()


    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Display selected model
    st.markdown(f"**Current Model:** {st.session_state.selected_model}")
    
    # Session controls
    st.markdown("### Session Controls")
    
    st.markdown("<div class='model-buttons'>", unsafe_allow_html=True)
    if st.button("🔄 Reset Conversation", key="new_chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.chat_started = False
        st.session_state.greeting_added = False
        st.session_state.followup_questions = []
        st.session_state.last_assistant = None
        st.session_state.pending_followup = None
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    if st.button("📝 Export Chat History", key="export_chat", use_container_width=True):
        # Generate markdown format
        markdown_text = get_chat_history_markdown()
        # Encode to download
        b64 = base64.b64encode(markdown_text.encode()).decode()
        file_name = f"future_proof_mentor_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        href = f'<a href="data:text/markdown;base64,{b64}" download="{file_name}">Click to download chat history (Markdown)</a>'
        st.markdown(href, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Main content
# Welcome card - ALWAYS show at the top regardless of chat status
st.title("🔮 Future Proof Mentor")
st.markdown("""
<div class="welcome-card">
    <div class="welcome-header">
        <div class="welcome-icon">🔮</div>
        <h2>Welcome to Future Proof Mentor</h2>
    </div>
    <div style="text-align: left; font-size: 18px; margin-top: 20px; line-height: 1.6;">
        As your strategic planning assistant, I can help you with:
        <ul style="list-style-position: inside; text-align: left; display: inline-block;">
            <li><strong>Scenario Planning</strong> - Map out multiple possible futures for your business</li>
            <li><strong>Trend Analysis</strong> - Identify emerging trends and weak signals of change</li>
            <li><strong>Risk Assessment</strong> - Evaluate threats and opportunities in different scenarios</li>
            <li><strong>Strategic Foresight</strong> - Develop adaptive strategies for an uncertain future</li>
        </ul>
        <p style="margin-top: 10px;"><b>To get started, enter your industry and what changes you're anticipating in the chat below.</b></p>
    </div>
</div>
""", unsafe_allow_html=True)

# Process a Pending Follow-Up (if any)
if st.session_state.pending_followup is not None:
    question = st.session_state.pending_followup
    st.session_state.pending_followup = None
    process_question(question)
    st.rerun()

# Display chat messages
if st.session_state.messages:
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(f"**You:** {message['content']}")
        elif message["role"] == "assistant":
            with st.chat_message("assistant"):
                # Process the response to add styling to references
                styled_response = re.sub(
                    r'\[(.*?)\]',
                    r'<span class="reference">[\1]</span>',
                    message['content']
                )
                st.markdown(
                    f"**Assistant:** {styled_response}",
                    unsafe_allow_html=True
                )

# Chat input
user_input = st.chat_input("Type your message here...")
if user_input:
    # Add greeting if it's the first message and hasn't been added yet
    if len(st.session_state.messages) == 0 and not st.session_state.greeting_added:
        # Add system greeting with the starting question
        greeting = "Hello! I'm your Future Proof Mentor. To get started, what industry is your business in? What are the biggest changes--technological, economic, regulatory, or social--that could impact it in the next 5-10 years?"
        st.session_state.messages.append({"role": "assistant", "content": greeting})
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": greeting, 
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.session_state.greeting_added = True
    
    # Process the user's question
    process_question(user_input)
    st.rerun()

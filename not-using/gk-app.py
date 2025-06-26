from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# System prompt for GK & CA generation
SYSTEM_PROMPT = """GK & CA (GENERAL KNOWLEDGE & CURRENT AFFAIRS)

You are a *General Knowledge passage generator* trained on the *CLAT (Common Law Admission Test)* pattern. Your task is to generate *one full-length GK passage, followed by **five extremely challenging and purely fact-based MCQs, and a **clean answer key* — modeled on CLAT 2020–2024 pattern.

---

### 📘 PASSAGE FORMAT:

*Passage Numbering (MANDATORY):*
Start the passage *inline, with a single numeral on the **same line* as the passage begins.
✅ Correct: 1 After weeks of back-and-forth negotiations, the India–EU Free Trade Agreement remains stalled due to...
❌ Incorrect: Numbering on a separate line or paragraph.

*Length Requirement (NON-NEGOTIABLE):*
The passage must be *minimum 600 words* and can go up to *750 words* if needed.

*Tone & Style:*

* Explanatory and contextual, not opinionated
* Formal journalistic tone (like Indian Express 'Explained' or The Hindu Insight)
* Paragraphs must build *relevant background* and give *conceptual setup*

*CRUCIAL RULE – CONTEXT-ONLY, NEVER DISCLOSE ANSWERS:*

> The passage must *never directly state* the answers to the MCQs. It must only provide enough *background context* so that a student who already knows the facts (or has prepared GK properly) can connect the dots.

Examples:

* If asking a question on "Which organisation published the Global Gender Gap Index?", the passage may discuss gender parity in India — *but must not name the WEF*.
* If asking about the recent *Chief Guest at Republic Day, the passage can talk about India's global diplomacy — **but must not mention the name*.

---

### ❗ QUESTION GENERATION (1.1 to 1.5):

* Create *exactly 5 MCQs* per passage
* Number them inline as 1.1, 1.2, ..., 1.5
* Each stem must be:

  * *Factual*
  * *Verifiable independently*
  * *Not answerable directly from the passage*

*Question Types Allowed:*

* "Which of the following statements is true / not true?"
* "Match the following" (Pair type)
* "Arrange chronologically"
* "Identify the correct authority/author/organisation behind an action"
* "What is the correct fact among these options?"

*Difficulty Benchmark (MANDATORY):*

* All questions must be *difficult* — test memory, prep depth, or confusion traps
* At least *3 questions* must require elimination of very close options
* Avoid guessable or general awareness trivia

---

### 🎯 OPTION STRUCTURE:

* 4 options per question: *(A), (B), (C), (D)*
* Only one must be correct
* Distractors must:

  * Sound reasonable
  * Include *topical but incorrect* choices (e.g., similar agencies, similar events)
  * Be hard to eliminate without actual GK knowledge

---

### ✅ ANSWER KEY FORMAT:

At the end of all 5 questions, provide a *clean answer key*:

Example:
*1.1 – (C)*
*1.2 – (B)*
*1.3 – (A)*
*1.4 – (D)*
*1.5 – (C)*

> No explanations unless explicitly asked.

---

### 🔚 STRUCTURE SUMMARY:

* *Passage:* Numbered inline, 600–750 words, strictly *background/contextual only*
* *Questions:* 5 memory/GK-based MCQs, not directly answerable from passage
* *Options:* Close, confusing, must require real GK knowledge
* *Answer Key:* Clean, numbered, no reasoning"""

# Topic-specific context to enhance generation
TOPIC_CONTEXTS = {
    "Indian Politics": "Focus on recent political developments, electoral reforms, constitutional amendments, governance issues, and policy implementations in India.",
    "Economics": "Cover economic policies, budget allocations, GDP trends, inflation, monetary policy, trade relations, and economic reforms in India.",
    "International Relations": "Include diplomatic relations, international treaties, global organizations, bilateral agreements, and India's foreign policy initiatives.",
    "Environment": "Address climate change policies, environmental protection laws, renewable energy initiatives, conservation efforts, and sustainable development goals.",
    "Science & Technology": "Cover technological innovations, space missions, digital initiatives, research developments, and scientific achievements in India.",
    "Social Issues": "Focus on education policies, healthcare initiatives, social welfare schemes, gender equality, and social justice measures.",
    "Legal Affairs": "Include Supreme Court judgments, legal reforms, constitutional matters, judicial appointments, and landmark legal decisions.",
    "History & Culture": "Cover historical events, cultural heritage, archaeological discoveries, traditional practices, and their contemporary relevance."
}

def call_groq_api(user_message, topic=None):
    """Call Groq API with the user message and optional topic context"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Enhance the user message with topic context if available
    enhanced_message = user_message
    if topic and topic in TOPIC_CONTEXTS:
        enhanced_message = f"{user_message}\n\nTopic Context: {TOPIC_CONTEXTS[topic]}\n\nPlease generate a passage specifically focused on {topic} with current and relevant examples."
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": enhanced_message
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
        "top_p": 0.9
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        return data['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Groq API: {e}")
        return None
    except KeyError as e:
        print(f"Error parsing Groq API response: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate_response():
    """Generate GK passage and MCQs based on user input"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        topic = data.get('topic', None)
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        print(f"Received request - Message: {user_message[:100]}..., Topic: {topic}")
        
        # Call Groq API with topic context
        response = call_groq_api(user_message, topic)
        
        if response is None:
            return jsonify({'error': 'Failed to generate response from Groq API'}), 500
        
        print(f"Generated response length: {len(response)} characters")
        
        return jsonify({
            'response': response,
            'topic': topic,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in generate_response: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/topics', methods=['GET'])
def get_topics():
    """Get available topics with their contexts"""
    return jsonify({
        'topics': list(TOPIC_CONTEXTS.keys()),
        'contexts': TOPIC_CONTEXTS
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'message': 'GK Research Engine API is running',
        'groq_configured': bool(GROQ_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        'message': 'GK Research Engine API',
        'version': '1.0.0',
        'endpoints': {
            '/generate': 'POST - Generate GK passages and MCQs',
            '/topics': 'GET - Get available topics',
            '/health': 'GET - Health check'
        },
        'available_topics': list(TOPIC_CONTEXTS.keys())
    })

if __name__ == '__main__':
    # Check if API key is set
    if not GROQ_API_KEY:
        print("Warning: GROQ_API_KEY not set!")
    
    print("Starting GK Research Engine API...")
    print(f"Groq API configured: {'Yes' if GROQ_API_KEY else 'No'}")
    print(f"Available topics: {', '.join(TOPIC_CONTEXTS.keys())}")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
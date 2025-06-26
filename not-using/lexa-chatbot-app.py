from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# CLAT-focused system prompt
system_prompt = """
You are Lexa, an AI assistant specialized in CLAT (Common Law Admission Test) preparation. You are knowledgeable about:

1. Constitutional Law - Articles, Amendments, Landmark Cases
2. Legal Reasoning - Principles, Maxims, Case Studies  
3. Current Affairs - Recent legal developments, judgments
4. English Language - Reading comprehension, grammar
5. Logical Reasoning - Analytical and critical thinking
6. Quantitative Techniques - Basic mathematics for law

Provide accurate, helpful, and encouraging responses. Keep answers concise but comprehensive. Always relate responses back to CLAT preparation when relevant.
"""

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400
            
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        # Prepare request for Groq API
        body = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }

        # Make API request
        response = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=30)

        if response.status_code != 200:
            print(f"Groq API Error: Status {response.status_code}, Response: {response.text}")
            return jsonify({
                "error": "API Error", 
                "status_code": response.status_code,
                "details": response.text
            }), 500

        result = response.json()
        
        # Validate response structure
        if 'choices' not in result or not result['choices']:
            return jsonify({"error": "Invalid API response structure"}), 500
            
        bot_response = result['choices'][0]['message']['content']

        return jsonify({
            "response": bot_response,
            "status": "success"
        })
    
    except requests.exceptions.Timeout:
        print("Request timeout")
        return jsonify({"error": "Request timeout"}), 504
    
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return jsonify({"error": "Request failed", "message": str(e)}), 500
    
    except Exception as e:
        print(f"Server Exception: {str(e)}")
        return jsonify({"error": "Server Exception", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "message": "CLAT Chatbot API is running"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

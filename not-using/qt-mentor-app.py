from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import traceback
import re
import os

app = Flask(__name__)
CORS(app)

# Your Groq API configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

system_prompt = """
You are a Quantitative Aptitude generator trained on the CLAT (Common Law Admission Test) pattern. Your task is to generate one complete Quantitative Aptitude passage, followed by exactly 6 multiple-choice questions, and a fully explained answer key.
donot say this is the generated or any bs like that
FORMAT REQUIREMENTS:
- Start passage with: "1 In recent years..." (number inline)
- Write 7-10 neutral tone sentences for the passage with realistic numerical data
- NO title for the passage

QUESTIONS FORMAT:
- Label questions as: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
- Each question must have exactly 4 options: (A), (B), (C), (D)
- Only one correct answer per question
- Questions should test analytical and calculation skills

ANSWER KEY FORMAT:
- Provide detailed step-by-step working
- Format: "1.1 – (B) [detailed explanation with calculations]"
- Include mathematical calculations where applicable
- Be thorough in explanations

EXAMPLE FORMAT:
1 In recent years, the XYZ company has seen significant growth...

1.1 What is the percentage increase in sales from 2020 to 2023?
(A) 25%
(B) 30%
(C) 35%
(D) 40%

1.2 If the company's profit margin is 15%, what was the profit in 2023?
(A) ₹150,000
(B) ₹200,000
(C) ₹250,000
(D) ₹300,000

[Continue for all 6 questions]

Answer Key:
1.1 – (B) To find the percentage increase: (New Value - Old Value)/Old Value × 100 = (1300-1000)/1000 × 100 = 30%

1.2 – (C) Profit = Revenue × Profit Margin = ₹1,666,667 × 15% = ₹250,000

[Continue for all answers]

IMPORTANT: Output must be directly readable text, NOT code. Generate content that matches CLAT examination standards with proper numerical data and realistic scenarios.
"""

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "CLAT QT Mentor API is running!", "status": "success"})

@app.route("/api/test", methods=["GET"])
def test_connection():
    return jsonify({
        "status": "success",
        "message": "API connection successful",
        "endpoint": "/api/generate-question"
    })

@app.route("/api/generate-question", methods=["POST"])
def generate_question():
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        topic = data.get("topic", "percentages")
        print(f"Received request for topic: {topic}")
        
        # Map frontend topics to more descriptive prompts
        topic_mapping = {
            "tables": "data interpretation using tables with numerical data including sales figures, population data, or financial statements",
            "bar-charts": "data interpretation using bar charts showing comparative analysis of multiple categories over time", 
            "line-graphs": "data interpretation using line graphs showing trend analysis over multiple years",
            "pie-charts": "data interpretation using pie charts showing percentage distribution of categories",
            "percentages": "percentage calculations including profit/loss, percentage changes, and percentage-based word problems",
            "ratios": "ratios, proportions, and comparative relationships with real-world applications",
            "averages": "mean, median, mode, and weighted averages with practical scenarios",
            "profit-loss": "profit and loss calculations including cost price, selling price, discount, and markup problems",
            "compound-interest": "compound interest, simple interest, and banking calculations with time-based scenarios",
            "time-work": "time and work problems including work rates, efficiency, and collaborative work scenarios",
            "speed-distance": "speed, distance, time problems including relative motion and average speed calculations"
        }
        
        detailed_topic = topic_mapping.get(topic, topic)
        print(f"Mapped to detailed topic: {detailed_topic}")

        # Enhanced user prompt for better quality
        user_prompt = f"""Generate a CLAT-style Quantitative Aptitude passage and exactly 6 questions on the topic: '{detailed_topic}'. 

Requirements:
1. Create a realistic business/economic scenario with specific numerical data
2. Passage should be 7-10 sentences with concrete numbers
3. Questions should progressively increase in difficulty
4. Each question must test different aspects of the topic
5. Ensure calculations are accurate and explanations are detailed
6. Use realistic Indian context (₹ currency, Indian companies/cities)

Topic focus: {detailed_topic}

Please follow the exact format specified in the system prompt."""

        # Prepare API request
        body = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4000,
            "top_p": 0.9
        }

        print("Making request to Groq API...")
        
        # Make API request with timeout
        response = requests.post(
            GROQ_API_URL, 
            headers=headers, 
            json=body, 
            timeout=45
        )
        
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            error_details = response.text
            print(f"Groq API Error {response.status_code}: {error_details}")
            return jsonify({
                "success": False,
                "error": f"API Error ({response.status_code})", 
                "details": error_details
            }), 500

        result = response.json()
        print("API Response received successfully")
        
        if 'choices' not in result or len(result['choices']) == 0:
            print("No choices in API response:", result)
            return jsonify({
                "success": False,
                "error": "Invalid API response", 
                "details": "No choices returned from API"
            }), 500
            
        content = result['choices'][0]['message']['content']
        print(f"Generated content length: {len(content)}")
        
        # Basic validation of generated content
        if not validate_content(content):
            print("Content validation failed")
            return jsonify({
                "success": False,
                "error": "Generated content doesn't meet quality standards",
                "details": "Please try generating again"
            }), 400

        return jsonify({
            "success": True,
            "rawOutput": content,
            "topic": topic,
            "contentLength": len(content)
        })
    
    except requests.exceptions.Timeout:
        print("Request timeout occurred")
        return jsonify({
            "success": False,
            "error": "Request timeout", 
            "message": "API request took too long. Please try again."
        }), 500
        
    except requests.exceptions.RequestException as e:
        print(f"Request exception: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Network error", 
            "message": f"Connection failed: {str(e)}"
        }), 500
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Server Exception", 
            "message": str(e)
        }), 500

def validate_content(content):
    """Basic validation to ensure content quality"""
    try:
        # Check if content has minimum length
        if len(content) < 500:
            return False
            
        # Check for presence of questions (1.1, 1.2, etc.)
        question_pattern = r'\d+\.\d+'
        questions = re.findall(question_pattern, content)
        if len(questions) < 6:
            return False
            
        # Check for presence of options
        option_pattern = r'\([A-D]\)'
        options = re.findall(option_pattern, content)
        if len(options) < 24:  # 6 questions × 4 options each
            return False
            
        # Check for answer key
        if 'Answer Key' not in content:
            return False
            
        return True
    except:
        return False

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/api/test", "/api/generate-question"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on the server"
    }), 500

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting CLAT QT Mentor Flask Server")
    print("📍 Server URL: http://127.0.0.1:5000")
    print("🔗 Test endpoint: http://127.0.0.1:5000/api/test")
    print("📝 Generate endpoint: http://127.0.0.1:5000/api/generate-question")
    print("=" * 60)
    app.run(debug=True, host="127.0.0.1", port=5000)
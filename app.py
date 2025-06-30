from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json
import os
import traceback
import re
from datetime import datetime
from fpdf import FPDF
from io import BytesIO
import tempfile
from flask import send_from_directory
from dotenv import load_dotenv

# Try to import PyMuPDF for PDF processing
try:
    import fitz  # PyMuPDF for PDF processing
    PDF_PROCESSING_AVAILABLE = True
    print("✅ PyMuPDF successfully imported - PDF processing enabled")
except ImportError as e:
    PDF_PROCESSING_AVAILABLE = False
    print(f"❌ Warning: PyMuPDF not available. PDF processing will be disabled. Error: {e}")
    print("💡 Try running: pip install PyMuPDF==1.24.3")
except Exception as e:
    PDF_PROCESSING_AVAILABLE = False
    print(f"❌ Unexpected error importing PyMuPDF: {e}")
    print("💡 Try running: pip install PyMuPDF==1.24.3")

app = Flask(__name__)
CORS(app)

# Environment configuration for Render
PORT = int(os.environ.get('PORT', 5000))
DEBUG = os.environ.get('FLASK_ENV') == 'development'

# Groq API configuration
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Startup check for API key
print(f"GROQ_API_KEY loaded: {'Yes' if GROQ_API_KEY else 'No'}")

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

@app.route("/")
def home():
    return send_from_directory('.', '1.land.html')

@app.route("/<path:filename>")
def serve_file(filename):
    return send_from_directory('.', filename)

# =============================================================================
# SYSTEM PROMPTS FOR DIFFERENT SERVICES
# =============================================================================

# GK Research Engine System Prompt
GK_SYSTEM_PROMPT = """GK & CA (GENERAL KNOWLEDGE & CURRENT AFFAIRS)

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

# Lexa Chatbot System Prompt
LEXA_SYSTEM_PROMPT = """
You are Lexa, an AI assistant specialized in CLAT (Common Law Admission Test) preparation. You are knowledgeable about:

1. Constitutional Law - Articles, Amendments, Landmark Cases
2. Legal Reasoning - Principles, Maxims, Case Studies  
3. Current Affairs - Recent legal developments, judgments
4. English Language - Reading comprehension, grammar
5. Logical Reasoning - Analytical and critical thinking
6. Quantitative Techniques - Basic mathematics for law

Provide accurate, helpful, and encouraging responses. Keep answers concise but comprehensive. Always relate responses back to CLAT preparation when relevant.
"""

# QT Mentor System Prompt
QT_SYSTEM_PROMPT = """
You are a Quantitative Aptitude generator trained on the CLAT (Common Law Admission Test) pattern. Your task is to generate one complete Quantitative Aptitude passage, followed by exactly 6 multiple-choice questions, and a fully explained answer key.
DO NOT say "this is the generated" or any similar phrases.

FORMAT REQUIREMENTS:
- Start passage with: "1 In recent years..." (number inline)
- Write 7-10 neutral tone sentences for the passage with realistic numerical data
- NO title for the passage
- DO NOT include any formatting symbols like #, *, or backslashes

QUESTIONS FORMAT:
- Label questions as: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
- Each question must have exactly 4 options: (A), (B), (C), (D)
- Only one correct answer per question
- Questions should test analytical and calculation skills

ANSWER KEY FORMAT:
- Provide extremely detailed, step-by-step explanations
- Format: "1.1 – (B) [VERY DETAILED EXPLANATION]"
- Explain as if teaching a 5-year-old child - use simple language, break down every step
- Each explanation should be AT LEAST 100-150 words
- Include all mathematical calculations with clear steps
- Use analogies and simple examples where helpful
- Explain WHY each step is taken, not just HOW
- Make it so simple that even someone with no math background can understand

EXAMPLE EXPLANATION STYLE:
"1.1 – (B) Let me explain this step by step, like I'm teaching a little kid! First, we need to understand what a percentage increase means. Think of it like this: if you had 10 candies yesterday and 13 candies today, how much more do you have? Well, you have 3 more candies, right? But we want to know what percentage that is. 

Here's the magic formula: (New Amount - Old Amount) ÷ Old Amount × 100 = Percentage Increase

Let's break this down:
Step 1: New Amount = 1300 (this is what we have now)
Step 2: Old Amount = 1000 (this is what we had before)
Step 3: Difference = 1300 - 1000 = 300 (this is how much more we have)
Step 4: Divide by old amount: 300 ÷ 1000 = 0.3
Step 5: Multiply by 100: 0.3 × 100 = 30%

So the answer is 30%, which is option (B). Think of it like this: for every 100 candies you had before, you now have 30 extra candies!"

IMPORTANT: Output must be directly readable text, NOT code. Generate content that matches CLAT examination standards with proper numerical data and realistic scenarios.
"""

# Fixed Sectional Test Generator Prompts with consistent formatting and answer key generation
SECTIONAL_PROMPTS = {
    "Reading Comprehension": """
You are a CLAT Reading Comprehension test generator.
Generate a passage of EXACTLY 500-600 words in a formal academic tone.
The passage should contain logical arguments, assumptions, and analytical content.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5).
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of why it is correct (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Detailed explanation text here explaining the reasoning step by step.

Follow this format exactly. Do not include any other headings or formatting symbols.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (C)
2. (B)
3. (A)
4. (D)
5. (C)
""",
    
    "Grammar": """
You are a CLAT English Grammar test generator.
Generate a passage of EXACTLY 300-400 words with grammatical concepts and examples.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing grammar rules.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the grammar rule (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Detailed explanation text here explaining the grammar rule step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (B)
2. (A)
3. (C)
4. (D)
5. (B)
""",
    
    "Vocabulary": """
You are a CLAT Vocabulary test generator.
Generate a passage of EXACTLY 300-400 words with advanced vocabulary words in context.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing vocabulary and word meanings.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the word meaning (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Detailed explanation text here explaining the word meaning step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (A)
2. (C)
3. (B)
4. (D)
5. (A)
""",
    
    "Para Jumbles": """
You are a CLAT Para Jumbles test generator.
Generate a passage of EXACTLY 300-400 words explaining para jumble concepts and provide examples.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) with para jumble exercises.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the correct sequence (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Detailed explanation text here explaining the correct sequence step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (D)
2. (A)
3. (C)
4. (B)
5. (D)
""",
    
    "Critical Reasoning": """
You are a CLAT Critical Reasoning test generator.
Generate a passage of EXACTLY 400-500 words with logical arguments and reasoning scenarios.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing critical reasoning skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the reasoning (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Detailed explanation text here explaining the reasoning step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (C)
2. (A)
3. (B)
4. (D)
5. (C)
""",
    
    "Logical Reasoning": """
You are a CLAT Logical Reasoning test generator.
Generate a passage of EXACTLY 400-500 words with logical scenarios and reasoning problems.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing logical reasoning.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the logic (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Detailed explanation text here explaining the logic step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (A)
2. (B)
3. (C)
4. (D)
5. (A)
""",
    
    "Legal Reasoning": """
You are a CLAT Legal Reasoning test generator.
Generate a passage of EXACTLY 400-500 words with legal scenarios and principles.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing legal reasoning.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the legal principle (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Detailed explanation text here explaining the legal principle step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (B)
2. (A)
3. (C)
4. (D)
5. (B)
""",
    
    "Quantitative Analysis": """
You are a CLAT Quantitative Analysis test generator.
Generate a passage of EXACTLY 300-400 words with mathematical concepts and problems.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing quantitative skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the calculation (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Detailed explanation text here explaining the calculation step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (C)
2. (A)
3. (B)
4. (D)
5. (C)
""",
    
    "General Knowledge": """
You are a CLAT General Knowledge test generator.
Generate a passage of EXACTLY 400-500 words with current affairs and static GK topics.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing general knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the fact or concept (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Detailed explanation text here explaining the fact or concept step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (A)
2. (B)
3. (C)
4. (D)
5. (A)
""",
    
    # Add specific topic prompts for quantitative
    "Percentages": """
You are a CLAT Percentages test generator.
Generate a passage of EXACTLY 300-400 words with percentage-based problems and concepts.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing percentage calculations.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the percentage calculation (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Detailed explanation text here explaining the percentage calculation step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (B)
2. (A)
3. (C)
4. (D)
5. (B)
""",
    
    "Arithmetic": """
You are a CLAT Arithmetic test generator.
Generate a passage of EXACTLY 300-400 words with arithmetic problems and concepts.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing arithmetic skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the arithmetic calculation (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Detailed explanation text here explaining the arithmetic calculation step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (C)
2. (A)
3. (B)
4. (D)
5. (C)
""",
    
    "Profit & Loss": """
You are a CLAT Profit & Loss test generator.
Generate a passage of EXACTLY 300-400 words with profit and loss problems and concepts.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing profit and loss calculations.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the profit/loss calculation (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Detailed explanation text here explaining the profit/loss calculation step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (A)
2. (B)
3. (C)
4. (D)
5. (A)
""",
    
    "Geometry": """
You are a CLAT Geometry test generator.
Generate a passage of EXACTLY 300-400 words with geometry problems and concepts.
DO NOT include any formatting symbols like #, *, or backslashes.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing geometry skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: detailed explanation of the geometry calculation (minimum 50 words).

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Detailed explanation text here explaining the geometry calculation step by step.

Follow this format exactly.

IMPORTANT: After all 5 questions, add a clean answer key section:

**ANSWER KEY**
1. (B)
2. (A)
3. (C)
4. (D)
5. (B)
"""
}

# =============================================================================
# TOPIC CONTEXTS FOR GK RESEARCH ENGINE
# =============================================================================

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
# =============================================================================
# SECTIONAL SUBCATEGORY MAPPING (Frontend -> Backend Labels)
# =============================================================================

SUBCATEGORY_MAPPINGS = {
    # English
    "main-idea": "Reading Comprehension",
    "author-s-tone": "Reading Comprehension",
    "vocab": "Vocabulary",
    "literary-and-poetic-devices": "Reading Comprehension",
    "author-based": "Reading Comprehension",
    "source-based": "Reading Comprehension",
    "title-theme": "Reading Comprehension",
    "direct-inference-questions": "Reading Comprehension",
    "assumptions-inferences": "Critical Reasoning",
    "idioms-mics": "Vocabulary",
    # Ensure all possible variants from frontend are mapped
    "title-theme": "Reading Comprehension",
    "literary-and-poetic-devices": "Reading Comprehension",
    "direct-inference-questions": "Reading Comprehension",
    "assumptions-inferences": "Critical Reasoning",
    "idioms-mics": "Vocabulary",

    # Logical
    "assumptions": "Critical Reasoning",
    "inferences": "Critical Reasoning",
    "argument-based": "Critical Reasoning",
    "agree-disagree": "Critical Reasoning",
    "strengthen-weaken": "Critical Reasoning",
    "direct-inference": "Logical Reasoning",
    "analogy-and-sequences": "Logical Reasoning",
    "paradox-contradiction-resolution": "Logical Reasoning",
    # Ensure all possible variants from frontend are mapped
    "argument-based": "Critical Reasoning",
    "agree-disagree": "Critical Reasoning",
    "strengthen-weaken": "Critical Reasoning",
    "direct-inference": "Logical Reasoning",
    "analogy-and-sequences": "Logical Reasoning",
    "paradox-contradiction-resolution": "Logical Reasoning",

    # Quantitative
    "percentage-comparison": "Percentages",
    "what-percentage-more-less": "Percentages",
    "percentage-change": "Percentages",
    "dividing-quantities-in-given-ratios": "Arithmetic",
    "missing-values-based-on-ratios": "Arithmetic",
    "simplification-of-numbers-to-derive-simplest-ratio": "Arithmetic",
    "simple-and-weighted-averages": "Arithmetic",
    "cost-price-selling-price-and-marked-price-calculations": "Profit & Loss",
    "discount-profit-loss": "Profit & Loss",
    "basic-formula-applications-of-simple-and-compound-interest": "Arithmetic",
    "area-perimeter-volume-and-surface-area": "Geometry",
    # Ensure all possible variants from frontend are mapped
    "simple-and-weighted-averages": "Arithmetic",
    "cost-price-selling-price-and-marked-price-calculations": "Profit & Loss",
    "discount-profit-loss": "Profit & Loss",
    "basic-formula-applications-of-simple-and-compound-interest": "Arithmetic",
    "area-perimeter-volume-and-surface-area": "Geometry",
    
    # Add direct mappings for single-subcategory cases
    "general-legal": "Legal Reasoning",
    "general-gk": "General Knowledge",
    
    # Add missing mappings for quantitative topics
    "percentages": "Percentages",
    "ratios": "Arithmetic",
    "averages": "Arithmetic",
    "profit-loss": "Profit & Loss",
    "compound-interest": "Arithmetic",
    "geometry": "Geometry",
    
    # Add mappings for GK topics
    "awards-honours": "General Knowledge",
    "science-tech": "General Knowledge",
    
    # Add missing mappings for practice-online
    "main-idea": "Reading Comprehension",
    "author-s-tone": "Reading Comprehension",
    "vocab": "Vocabulary",
    "literary-and-poetic-devices": "Reading Comprehension",
    "author-based": "Reading Comprehension",
    "source-based": "Reading Comprehension",
    "title-theme": "Reading Comprehension",
    "direct-inference-questions": "Reading Comprehension",
    "assumptions-inferences": "Critical Reasoning",
    "idioms-mics": "Vocabulary",
    "assumptions": "Critical Reasoning",
    "inferences": "Critical Reasoning",
    "argument-based": "Critical Reasoning",
    "agree-disagree": "Critical Reasoning",
    "strengthen-weaken": "Critical Reasoning",
    "direct-inference": "Logical Reasoning",
    "analogy-and-sequences": "Logical Reasoning",
    "paradox-contradiction-resolution": "Logical Reasoning",
    "percentage-comparison": "Percentages",
    "what-percentage-more-less": "Percentages",
    "percentage-change": "Percentages",
    "dividing-quantities-in-given-ratios": "Arithmetic",
    "missing-values-based-on-ratios": "Arithmetic",
    "simplification-of-numbers-to-derive-simplest-ratio": "Arithmetic",
    "simple-and-weighted-averages": "Arithmetic",
    "cost-price-selling-price-and-marked-price-calculations": "Profit & Loss",
    "discount-profit-loss": "Profit & Loss",
    "basic-formula-applications-of-simple-and-compound-interest": "Arithmetic",
    "area-perimeter-volume-and-surface-area": "Geometry",
}

# =============================================================================
# QT MENTOR TOPIC MAPPING
# =============================================================================

QT_TOPIC_MAPPING = {
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

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
                                                              
def call_groq_api(messages, temperature=0.7, max_tokens=4000):
    """Generic function to call Groq API"""
    if not GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY is not set. Cannot call Groq API.")
        return None
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.9
    }
                                                              
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        return data['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Groq API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Groq API response: {e.response.text}")
        return None
    except KeyError as e:
        print(f"Error parsing Groq API response: {e}")
        return None

def validate_qt_content(content):
    """Basic validation to ensure QT content quality"""
    try:
        # Check if content has minimum length
        if len(content) < 500:
            return False
        return True
    except:
        return False

def clean_formatting_artifacts(text):
    """Clean up formatting artifacts from AI-generated content"""
    if not text:
        return text
    
    # Remove common formatting artifacts
    cleaned = text
    
    # Remove backslashes that are not part of valid escape sequences
    cleaned = re.sub(r'\\(?!n|t|r|\\|"|\')', '', cleaned)
    
    # Remove hashtags and markdown symbols that shouldn't be visible
    cleaned = re.sub(r'#+', '', cleaned)  # Remove hashtags
    cleaned = re.sub(r'\*\*(?!MCQs|ANSWER KEY)', '', cleaned)  # Remove ** except for MCQs and ANSWER KEY
    cleaned = re.sub(r'\*(?!\()', '', cleaned)  # Remove * except for option markers like (A)
    
    # Remove extra whitespace and normalize line breaks
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Remove excessive line breaks
    cleaned = re.sub(r' +', ' ', cleaned)  # Remove multiple spaces
    
    # Clean up the text
    cleaned = cleaned.strip()
    
    return cleaned

def generate_study_material(topic, count):
    """Generate study material for sectional tests"""
    all_sections = []
    for i in range(count):
        print(f"📝 Generating section {i+1}/{count} for {topic}...")
        mapped_topic = SUBCATEGORY_MAPPINGS.get(topic or "", topic or "")
        prompt = SECTIONAL_PROMPTS.get(mapped_topic, f"Generate a CLAT-level {mapped_topic} test with passage, questions, and answer key.")

        # Add more explicit instructions to ensure format compliance
        enhanced_prompt = f"""
{prompt}

CRITICAL: You MUST follow this exact format:
1. Write a passage first
2. Then add the line: **MCQs**
3. Then write 5 numbered questions (1. 2. 3. 4. 5.)
4. Each question must have options (A) (B) (C) (D)
5. Each question must have "Answer: (X)" and "Explanation: ..."
6. Finally add: **ANSWER KEY** followed by numbered answers

DO NOT deviate from this format. The **MCQs** marker is essential for parsing.
"""

        messages = [
            {"role": "system", "content": "You are an expert CLAT study material generator. You MUST follow the exact format specified in the prompt."},
            {"role": "user", "content": enhanced_prompt}
        ]
        result = call_groq_api(messages)
        if result:
            # Clean up formatting artifacts
            cleaned_result = clean_formatting_artifacts(result)
            print(f"[DEBUG] Raw AI response length: {len(result)}")
            print(f"[DEBUG] Cleaned response length: {len(cleaned_result)}")
            print(f"[DEBUG] Response preview: {cleaned_result[:300]}...")
            
            # Check if response contains MCQs section
            if "**MCQs**" in cleaned_result:
                print(f"[DEBUG] ✅ MCQs section found")
            else:
                print(f"[DEBUG] ❌ MCQs section NOT found")
                print(f"[DEBUG] Full response: {cleaned_result}")
            
            all_sections.append(f"Topic: {topic}\n\n{cleaned_result.strip()}")
        else:
            print(f"❌ Failed to generate section {i+1}")
    return all_sections

def parse_mcqs(raw_text):
    """Parse MCQs from raw text - IMPROVED ROBUST VERSION"""
    try:
        # First try to find the **MCQs** section
        parts = re.split(r'\*\*MCQs\*\*', raw_text)
        if len(parts) < 2:
            print("[DEBUG] No **MCQs** section found, trying alternative parsing")
            # If no **MCQs** section, try to find questions directly
            mcqs_text = raw_text
            # Try to extract passage from the beginning before any numbered questions
            passage_match = re.search(r'^(.+?)(?=\n\d+\.|\nQuestion|\n[A-D]\.|\n\([A-D]\)|\Z)', raw_text, re.DOTALL)
            passage = passage_match.group(1).strip() if passage_match else "Passage not found"
        else:
            passage = parts[0].strip()
            mcqs_text = parts[1].strip()

        # Remove the answer key section from MCQs text to avoid parsing it as questions
        mcqs_text = re.sub(r'\*\*ANSWER KEY\*\*.*', '', mcqs_text, flags=re.DOTALL)
        mcqs_text = mcqs_text.strip()

        # Try multiple patterns to find questions
        question_patterns = [
            r'(\d+\..*?)(?=\n\d+\.|\Z)',  # Standard numbered questions
            r'(\d+\)\s*.*?)(?=\n\d+\)|\Z)',  # Questions with parentheses
            r'(Question\s*\d+.*?)(?=Question\s*\d+|\Z)',  # "Question X" format
        ]
        
        question_blocks = []
        for pattern in question_patterns:
            question_blocks = re.findall(pattern, mcqs_text, re.DOTALL)
            if question_blocks:
                print(f"[DEBUG] Found {len(question_blocks)} question blocks using pattern: {pattern}")
                break
        
        if not question_blocks:
            print("[DEBUG] No question blocks found with any pattern")
            print(f"[DEBUG] Raw text preview: {raw_text[:500]}...")
            return []

        structured_questions = []

        for idx, block in enumerate(question_blocks, start=1):
            try:
                # Skip blocks that are just answer key entries (like "1. (A)")
                if re.match(r'^\d+\.\s*\([A-D]\)\s*$', block.strip()) or re.match(r'^\d+\)\s*\([A-D]\)\s*$', block.strip()):
                    print(f"[DEBUG] Skipping answer key block: {block.strip()}")
                    continue
                
                # Look for question text before first option (A)
                q_patterns = [
                    r'\d+\.\s*(.+?)\n\(A\)',  # Standard format with (A)
                    r'\d+\)\s*(.+?)\n\(A\)',  # Parentheses format with (A)
                    r'Question\s*\d+.*?\n(.+?)\n\(A\)',  # Question format with (A)
                    r'\d+\.\s*(.+?)\nA\.',  # Standard format with A.
                    r'\d+\)\s*(.+?)\nA\.',  # Parentheses format with A.
                    r'Question\s*\d+.*?\n(.+?)\nA\.',  # Question format with A.
                ]
                
                question = "Unknown question"
                for q_pattern in q_patterns:
                    q_match = re.search(q_pattern, block, re.DOTALL)
                    if q_match:
                        question = q_match.group(1).strip()
                        break

                # Skip if this doesn't look like a real question
                if question == "Unknown question" or len(question) < 10:
                    print(f"[DEBUG] Skipping invalid question block: {block[:100]}...")
                    continue

                options = []
                for opt in ['A', 'B', 'C', 'D']:
                    # Match: (A) Option text until the next (B)/(C)/(D)/Answer/End
                    opt_patterns = [
                        rf'\({opt}\)\s*(.+?)(?=\n\([A-D]\)|\nAnswer:|\Z)',  # (A) format
                        rf'{opt}\)\s*(.+?)(?=\n[A-D]\)|\nAnswer:|\Z)',  # A) format
                        rf'{opt}\.\s*(.+?)(?=\n[A-D]\.|\nAnswer:|\Z)',  # A. format
                    ]
                    
                    option_text = f"Option ({opt}) text missing"
                    for opt_pattern in opt_patterns:
                        opt_match = re.search(opt_pattern, block, re.DOTALL)
                        if opt_match:
                            option_text = opt_match.group(1).strip()
                            break
                    options.append(option_text)

                # Look for answer in multiple formats
                ans_patterns = [
                    r'Answer:\s*\(([A-D])\)',
                    r'Answer:\s*([A-D])',
                    r'Correct Answer:\s*\(([A-D])\)',
                    r'Correct Answer:\s*([A-D])',
                ]
                
                correct_letter = 'A'
                for ans_pattern in ans_patterns:
                    ans_match = re.search(ans_pattern, block)
                    if ans_match:
                        correct_letter = ans_match.group(1)
                        break
                
                correct_index = ord(correct_letter) - ord('A')

                # Look for explanation
                exp_patterns = [
                    r'Explanation:\s*(.+)',
                    r'Solution:\s*(.+)',
                    r'Reasoning:\s*(.+)',
                ]
                
                explanation = "Explanation not available"
                for exp_pattern in exp_patterns:
                    exp_match = re.search(exp_pattern, block, re.DOTALL)
                    if exp_match:
                        explanation = exp_match.group(1).strip()
                        break

                structured_questions.append({
                    "id": idx,
                    "passage": passage,
                    "question": question,
                    "options": options,
                    "correct": correct_index,
                    "explanation": explanation
                })
                
                print(f"[DEBUG] Successfully parsed Q{idx}: {question[:50]}...")
                
            except Exception as e:
                print(f"[ERROR PARSING Q{idx}]: {e}")
                print(f"[DEBUG BLOCK]: {block[:200]}...")
                continue

        print(f"[DEBUG] Successfully parsed {len(structured_questions)} questions")
        return structured_questions
        
    except Exception as e:
        print(f"[ERROR in parse_mcqs]: {e}")
        return []

def parse_answer_key(raw_text):
    """Parse answer key from raw text (robust version)"""
    try:
        # Look for the answer key section
        answer_key_match = re.search(r'\*\*ANSWER KEY\*\*\s*\n(.*?)(?=\n\n|\Z)', raw_text, re.DOTALL)
        if not answer_key_match:
            print("[DEBUG] No **ANSWER KEY** section found")
            return []
        
        answer_key_text = answer_key_match.group(1).strip()
        
        # Parse individual answers: 1. (A), 1. A, 1) A, 1 : A, etc.
        answers = []
        answer_patterns = [
            r'(\d+)\.\s*\(([A-D])\)',   # 1. (A)
            r'(\d+)\.\s*([A-D])',         # 1. A
            r'(\d+)\)\s*([A-D])',         # 1) A
            r'(\d+)\s*[:-]\s*([A-D])',    # 1 : A or 1 - A
        ]
        for pattern in answer_patterns:
            matches = re.findall(pattern, answer_key_text)
            for question_num, answer_letter in matches:
                answers.append({
                    "question": int(question_num),
                    "answer": answer_letter,
                    "answer_index": ord(answer_letter) - ord('A')
                })
        print(f"[DEBUG] Successfully parsed {len(answers)} answer key entries")
        return answers
        
    except Exception as e:
        print(f"[ERROR in parse_answer_key]: {e}")
        return []

def create_answer_key_pdf(questions, answer_key, test_metadata):
    """Create answer key PDF with watermark image and professional formatting using PyMuPDF only."""
    try:
        if 'fitz' not in globals() or not PDF_PROCESSING_AVAILABLE:
            raise RuntimeError("PyMuPDF is required for watermark-based PDF generation.")

        import fitz
        from io import BytesIO
        import os

        logo_path = os.path.join("images", "CLAT COMMUNITY ILLUSTRATED LOGO .png")
        # Open the image and get its size
        logo_img = fitz.Pixmap(logo_path)

        # PDF page size (A4: 612x792 points)
        page_width, page_height = 612, 792

        # Calculate watermark size (scale to 60% of page width, keep aspect ratio)
        max_logo_width = page_width * 0.6
        scale = max_logo_width / logo_img.width
        logo_width = int(logo_img.width * scale)
        logo_height = int(logo_img.height * scale)
        logo_x = (page_width - logo_width) // 2
        logo_y = (page_height - logo_height) // 2

        # Create new PDF
        result_pdf = fitz.open()
        page = result_pdf.new_page(width=page_width, height=page_height)

        # Draw watermark (20% opacity)
        page.insert_image(
            fitz.Rect(logo_x, logo_y, logo_x + logo_width, logo_y + logo_height),
            pixmap=logo_img,
            overlay=False,
            opacity=0.2
        )
        logo_img = None  # Free memory

        # --- Layout constants ---
        margin_x = 50
        y = 60
        line_height = 18
        font = "helv"
        font_bold = "helv"
        font_size_title = 28
        font_size_header = 16
        font_size_table = 13
        font_size_normal = 12
        color_black = (0, 0, 0)

        # Title
        page.insert_textbox(
            fitz.Rect(margin_x, y, page_width - margin_x, y + 40),
            "Answer Key",
            fontname=font_bold,
            fontsize=font_size_title,
            align=1,  # center
            color=color_black
        )
        y += 45

        # Answer Key Summary Header
        page.insert_textbox(
            fitz.Rect(margin_x, y, page_width - margin_x, y + line_height),
            "Answer Key Summary:",
            fontname=font_bold,
            fontsize=font_size_header,
            color=color_black
        )
        y += line_height + 5

        # Table headers
        col1_x = margin_x
        col2_x = margin_x + 70
        col3_x = margin_x + 130
        col1_w = 60
        col2_w = 50
        col3_w = page_width - margin_x - col3_x  # fill remaining width
        table_y = y
        page.insert_textbox(
            fitz.Rect(col1_x, table_y, col1_x + col1_w, table_y + line_height),
            "Question", fontsize=font_size_table, fontname=font_bold, color=color_black, align=1
        )
        page.insert_textbox(
            fitz.Rect(col2_x, table_y, col2_x + col2_w, table_y + line_height),
            "Answer", fontsize=font_size_table, fontname=font_bold, color=color_black, align=1
        )
        page.insert_textbox(
            fitz.Rect(col3_x, table_y, col3_x + col3_w, table_y + line_height),
            "Correct Option", fontsize=font_size_table, fontname=font_bold, color=color_black, align=1
        )
        y += line_height

        # Table content
        for i, answer in enumerate(answer_key, 1):
            question_num = answer.get('question', str(i))
            answer_letter = answer.get('answer', 'N/A')
            answer_index = answer.get('answer_index', 0)
            correct_option = "N/A"
            if i <= len(questions):
                question = questions[i-1]
                if 'options' in question and answer_index < len(question['options']):
                    correct_option = question['options'][answer_index]
            # Insert each cell as a textbox to wrap text
            page.insert_textbox(
                fitz.Rect(col1_x, y, col1_x + col1_w, y + line_height),
                f"Q{question_num}", fontsize=font_size_table, fontname=font, color=color_black, align=1
            )
            page.insert_textbox(
                fitz.Rect(col2_x, y, col2_x + col2_w, y + line_height),
                answer_letter, fontsize=font_size_table, fontname=font, color=color_black, align=1
            )
            # Correct Option: wrap and allow up to 2 lines
            bbox = fitz.Rect(col3_x, y, col3_x + col3_w, y + 2*line_height)
            page.insert_textbox(
                bbox,
                correct_option,
                fontsize=font_size_table,
                fontname=font,
                color=color_black,
                align=0
            )
            y += 2*line_height  # allow for wrapping

        y += 15

        # Detailed Explanations Header
        page.insert_textbox(
            fitz.Rect(margin_x, y, page_width - margin_x, y + line_height),
            "Detailed Explanations:",
            fontname=font_bold,
            fontsize=font_size_header,
            color=color_black
        )
        y += line_height + 5

        # Explanations
        for i, question in enumerate(questions, 1):
            if y > page_height - 120:
                # Add new page with watermark
                page = result_pdf.new_page(width=page_width, height=page_height)
                logo_img = fitz.Pixmap(logo_path)
                page.insert_image(
                    fitz.Rect(logo_x, logo_y, logo_x + logo_width, logo_y + logo_height),
                    pixmap=logo_img,
                    overlay=False,
                    opacity=0.2
                )
                logo_img = None
                y = 60
            # Question number
            page.insert_text((margin_x, y), f"Question {i}:", fontsize=font_size_table, fontname=font_bold, color=color_black)
            y += line_height - 4
            # Question text
            question_text = question.get('question', 'Question text not available')
            y = page.insert_textbox(
                fitz.Rect(margin_x, y, page_width - margin_x, y + 3*line_height),
                f"Q: {question_text}",
                fontname=font,
                fontsize=font_size_normal,
                color=color_black
            ).y1 + 2
            # Options
            options = question.get('options', [])
            for j, option in enumerate(options):
                option_letter = chr(65 + j)
                is_correct = j == question.get('correct', 0)
                option_text = f"{option_letter}. {option}"
                font_used = font_bold if is_correct else font
                y = page.insert_textbox(
                    fitz.Rect(margin_x + 10, y, page_width - margin_x, y + 2*line_height),
                    option_text,
                    fontname=font_used,
                    fontsize=font_size_normal,
                    color=color_black
                ).y1 + 1
            # Correct answer
            correct_index = question.get('correct', 0)
            correct_letter = chr(65 + correct_index)
            y = page.insert_textbox(
                fitz.Rect(margin_x, y, page_width - margin_x, y + line_height),
                f"Correct Answer: {correct_letter}",
                fontname=font_bold,
                fontsize=font_size_normal,
                color=color_black
            ).y1 + 2
            # Explanation
            explanation = question.get('explanation', 'No explanation available.')
            y = page.insert_textbox(
                fitz.Rect(margin_x, y, page_width - margin_x, y + 3*line_height),
                f"Explanation: {explanation}",
                fontname=font,
                fontsize=font_size_normal,
                color=color_black
            ).y1 + 8
        # Footer
        page.insert_textbox(
            fitz.Rect(margin_x, page_height - 40, page_width - margin_x, page_height - 10),
            'Generated by CLAT.GPT.1 - For more material visit: https://discord.gg/9kFymfz7qN\nContact: 7702832727 | Telegram: https://t.me/CLAT_Community',
            fontname=font,
            fontsize=9,
            color=(0.3, 0.3, 0.3),
            align=1
        )
        output_bytes = result_pdf.write()
        result_pdf.close()
        return BytesIO(output_bytes)
    except Exception as e:
        print(f"[ERROR in create_answer_key_pdf]: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_pdf(contents, title):
    """Create PDF from content with improved formatting"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    try:
        font_path = "DejaVuSans.ttf"
        if os.path.exists(font_path):
            pdf.add_font("DejaVu", "", font_path, uni=True)
            pdf.set_font("DejaVu", size=12)
        else:
            pdf.set_font("Arial", size=12)
    except:
        pdf.set_font("Arial", size=12)
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, title, ln=True, align='C')
    pdf.ln(10)
    
    # Content
    pdf.set_font("Arial", '', 12)
    for section in contents:
        try:
            clean = section.encode('latin1', 'replace').decode('latin1')
        except:
            clean = section
        pdf.multi_cell(0, 10, clean)
        pdf.ln(5)
    
    # Add footer
    pdf.set_y(-30)
    pdf.set_font("Arial", '', 8)
    pdf.set_text_color(107, 114, 128)
    pdf.cell(0, 5, 'Generated by CLAT.GPT.1 - For more material visit: https://discord.gg/9kFymfz7qN', ln=True, align='C')
    pdf.cell(0, 5, 'Contact: 7702832727 | Telegram: https://t.me/CLAT_Community', ln=True, align='C')
    
    return BytesIO(pdf.output(dest='S'))

# =============================================================================
# MAIN ROUTES
# =============================================================================

# @app.route("/status", methods=["GET"])
# def api_info():
#     """Main home endpoint"""
#     return jsonify({
#         "message": "CLAT Unified API - All Services Running",
#         "version": "2.0.1",
#         "services": {
#             "gk_research": "Generate GK passages and MCQs",
#             "lexa_chatbot": "CLAT-focused AI assistant",
#             "qt_mentor": "Quantitative Aptitude question generator",
#             "sectional_tests": "Generate sectional practice tests"
#         },
#         "endpoints": {
#             # GK Research Engine
#             "/gk/generate": "POST - Generate GK passages and MCQs",
#             "/gk/topics": "GET - Get available GK topics",
#             "/gk/assistant": "POST - GK study assistant",
#             "/gk/upload-pdf": "POST - Upload PDF for GK generation",
            
#             # Lexa Chatbot
#             "/lexa/chat": "POST - Chat with Lexa assistant",
            
#             # QT Mentor
#             "/qt/generate-question": "POST - Generate QT questions",
#             "/qt/test": "GET - Test QT service",
            
#             # Sectional Tests
#             "/generate-test": "POST - Generate sectional tests",
#             "/download-pdf": "POST - Download test as PDF",
#             "/topics": "GET - Get all available topics",
#             "/api/generate-practice": "POST - Generate practice questions",
#             "/test-parser": "GET - Test MCQ parser",
            
#             # Health
#             "/health": "GET - Health check for all services"
#         },
#         "status": "All services operational"
#     })

# =============================================================================
# GK RESEARCH ENGINE ROUTES
# =============================================================================

@app.route('/gk/generate', methods=['POST'])
def gk_generate_response():
    """Generate GK passage based on user input"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        topic = data.get('topic', None)
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        print(f"GK Request - Message: {user_message[:100]}..., Topic: {topic}")
        
        # Enhance the user message with topic context if available
        enhanced_message = user_message
        if topic and topic in TOPIC_CONTEXTS:
            enhanced_message = f"{user_message}\n\nTopic Context: {TOPIC_CONTEXTS[topic]}\n\nPlease generate a passage specifically focused on {topic} with current and relevant examples."
        
        messages = [
            {"role": "system", "content": GK_SYSTEM_PROMPT},
            {"role": "user", "content": enhanced_message}
        ]
        
        response = call_groq_api(messages)
        
        if response is None:
            return jsonify({'error': 'Failed to generate response from Groq API'}), 500
        
        # Clean up formatting artifacts
        cleaned_response = clean_formatting_artifacts(response)
        
        print(f"GK Generated response length: {len(cleaned_response)} characters")
        
        return jsonify({
            'response': cleaned_response,
            'topic': topic,
            'timestamp': datetime.now().isoformat(),
            'service': 'gk_research'
        })
        
    except Exception as e:
        print(f"Error in gk_generate_response: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/gk/assistant', methods=['POST'])
def gk_study_assistant():
    """GK Study Assistant"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Message is empty'}), 400
        if not GROQ_API_KEY:
            return jsonify({'error': 'GROQ_API_KEY is not set on the server. Please contact admin.'}), 500
        print(f"Study Assistant Request: {user_message[:100]}...")
        assistant_prompt = """You are a CLAT study assistant. \nYour job is to:\n- Explain topics in simple, structured, academic style\n- Summarize passages or documents clearly\n- Help students understand, take notes, or break down complex issues\nDo NOT generate questions unless explicitly asked.\n"""
        messages = [
            {"role": "system", "content": assistant_prompt},
            {"role": "user", "content": user_message}
        ]
        response = call_groq_api(messages)
        if response is None:
            return jsonify({'error': 'Failed to generate assistant response. Please check GROQ_API_KEY and Groq API status.'}), 500
        
        # Clean up formatting artifacts
        cleaned_response = clean_formatting_artifacts(response)
        
        return jsonify({
            'response': cleaned_response,
            'service': 'gk_assistant',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Study assistant error: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/gk/topics', methods=['GET'])
def gk_get_topics():
    """Get available GK topics with their contexts"""
    return jsonify({
        'topics': list(TOPIC_CONTEXTS.keys()),
        'contexts': TOPIC_CONTEXTS,
        'service': 'gk_research'
    })

@app.route('/gk/upload-pdf', methods=['POST'])
def gk_upload_pdf():
    """Upload PDF for GK generation"""
    try:
        print(f"PDF upload request received. PDF_PROCESSING_AVAILABLE: {PDF_PROCESSING_AVAILABLE}")
        
        if not PDF_PROCESSING_AVAILABLE:
            print("❌ PDF processing not available - PyMuPDF import failed")
            return jsonify({
                'error': 'PDF processing not available',
                'message': 'PyMuPDF library is not installed or not accessible. Please install it to enable PDF processing.',
                'debug_info': {
                    'pdf_processing_available': False,
                    'suggestion': 'Run: pip install PyMuPDF==1.24.3'
                }
            }), 400

        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file.filename or not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        print(f"Processing PDF: {file.filename}")

        # Save the uploaded file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        file.save(temp_file.name)
        temp_file.close()

        try:
            # Extract text from PDF using PyMuPDF
            print("Opening PDF with PyMuPDF...")
            doc = fitz.open(temp_file.name)
            text_content = ""
            
            print(f"PDF has {len(doc)} pages")
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                text_content += page_text
                print(f"Page {page_num + 1}: {len(page_text)} characters")
            
            doc.close()
            
            # Clean up temporary file
            os.unlink(temp_file.name)
            
            print(f"Total extracted text: {len(text_content)} characters")
            
            # Limit text content to reasonable length (first 2000 characters)
            if len(text_content) > 2000:
                text_content = text_content[:2000] + "..."
            
            # Generate GK content based on the PDF text
            user_prompt = f"""Based on the following PDF content, generate a CLAT-style GK passage with 5 MCQs and answer key. 
            
PDF Content:
{text_content}

Please create:
1. A 600-750 word passage on the main topic from the PDF
2. 5 challenging MCQs (1.1 to 1.5) based on the content
3. A clean answer key

Focus on the most important facts and current affairs from the PDF content."""

            messages = [
                {"role": "system", "content": GK_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
            
            print("Generating GK content with Groq API...")
            response = call_groq_api(messages, temperature=0.7, max_tokens=4000)
            
            if response is None:
                return jsonify({'error': 'Failed to generate content from PDF'}), 500
            
            # Clean up formatting artifacts
            cleaned_response = clean_formatting_artifacts(response)
            
            print("✅ PDF processing completed successfully")
            
            return jsonify({
                'response': cleaned_response,
                'pdf_filename': file.filename,
                'extracted_text_length': len(text_content),
                'status': 'success'
            })
            
        except Exception as pdf_error:
            # Clean up temporary file on error
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            print(f"❌ PDF processing error: {pdf_error}")
            raise pdf_error

    except Exception as e:
        print(f"❌ PDF upload error: {e}")
        return jsonify({
            'error': f'Error processing PDF: {str(e)}',
            'debug_info': {
                'pdf_processing_available': PDF_PROCESSING_AVAILABLE,
                'error_type': type(e).__name__
            }
        }), 500

# =============================================================================
# LEXA CHATBOT ROUTES
# =============================================================================

@app.route("/lexa/chat", methods=["POST"])
def lexa_chat():
    """Chat with Lexa CLAT assistant"""
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
        if not GROQ_API_KEY:
            return jsonify({"error": "GROQ_API_KEY is not set on the server. Please contact admin."}), 500
        print(f"Lexa Chat - Message: {user_message[:100]}...")
        messages = [
            {"role": "system", "content": LEXA_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        response = call_groq_api(messages, temperature=0.7, max_tokens=1024)
        if response is None:
            return jsonify({"error": "Failed to get response from Lexa. Please check GROQ_API_KEY and Groq API status."}), 500
        
        # Clean up formatting artifacts
        cleaned_response = clean_formatting_artifacts(response)
        
        return jsonify({
            "response": cleaned_response,
            "status": "success",
            "service": "lexa_chatbot",
            "timestamp": datetime.now().isoformat()
        })
    except requests.exceptions.Timeout:
        print("Lexa request timeout")
        return jsonify({"error": "Request timeout"}), 504
    except Exception as e:
        print(f"Lexa Server Exception: {str(e)}")
        return jsonify({"error": "Server Exception", "message": str(e)}), 500

# =============================================================================
# QT MENTOR ROUTES
# =============================================================================

@app.route("/qt/test", methods=["GET"])
def qt_test_connection():
    """Test QT Mentor connection"""
    return jsonify({
        "status": "success",
        "message": "QT Mentor API connection successful",
        "service": "qt_mentor",
        "available_topics": list(QT_TOPIC_MAPPING.keys())
    })

@app.route("/qt/generate-question", methods=["POST"])
def qt_generate_question():
    """Generate QT questions based on topic"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        topic = data.get("topic", "percentages")
        print(f"QT Request for topic: {topic}")
        detailed_topic = QT_TOPIC_MAPPING.get(topic, topic)
        print(f"QT Mapped to detailed topic: {detailed_topic}")
        if not GROQ_API_KEY:
            return jsonify({"success": False, "error": "GROQ_API_KEY is not set on the server. Please contact admin.", "service": "qt_mentor"}), 500
        # Enhanced user prompt for better quality
        user_prompt = f"""Generate a CLAT-style Quantitative Aptitude passage and exactly 6 questions on the topic: '{detailed_topic}'. \n\nRequirements:\n1. Create a realistic business/economic scenario with specific numerical data\n2. Passage should be 7-10 sentences with concrete numbers\n3. Questions should progressively increase in difficulty\n4. Each question must test different aspects of the topic\n5. Ensure calculations are accurate and explanations are detailed\n6. Use realistic Indian context (₹ currency, Indian companies/cities)\n\nTopic focus: {detailed_topic}\n\nPlease follow the exact format specified in the system prompt."""
        messages = [
            {"role": "system", "content": QT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        print("Making QT request to Groq API...")
        response = call_groq_api(messages, temperature=0.7, max_tokens=4000)
        if response is None:
            return jsonify({
                "success": False,
                "error": "Failed to generate QT content. Please check GROQ_API_KEY and Groq API status.",
                "service": "qt_mentor"
            }), 500
        print(f"QT Generated content length: {len(response)}")
        
        # Clean up formatting artifacts
        cleaned_response = clean_formatting_artifacts(response)
        
        # Basic validation of generated content
        if not validate_qt_content(cleaned_response):
            print("QT Content validation failed")
            return jsonify({
                "success": False,
                "error": "Generated content doesn't meet quality standards",
                "details": "Please try generating again",
                "service": "qt_mentor"
            }), 400
        return jsonify({
            "success": True,
            "rawOutput": cleaned_response,
            "topic": topic,
            "contentLength": len(cleaned_response),
            "service": "qt_mentor",
            "timestamp": datetime.now().isoformat()
        })
    except requests.exceptions.Timeout:
        print("QT Request timeout occurred")
        return jsonify({
            "success": False,
            "error": "Request timeout", 
            "message": "API request took too long. Please try again.",
            "service": "qt_mentor"
        }), 500
    except Exception as e:
        print(f"QT Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Server Exception", 
            "message": str(e),
            "service": "qt_mentor"
        }), 500

# =============================================================================
# SECTIONAL TEST GENERATOR ROUTES
# =============================================================================
@app.route("/generate-test", methods=['POST'])
def generate_content():
    """Generate sectional test content with answer key"""
    try:
        data = request.get_json()
        topic = data.get('topic') or data.get('subcategory')
        if not topic:
            return jsonify({'error': 'Topic is missing'}), 400

        # ✅ Do NOT convert with .title(), just map raw
        mapped_topic = SUBCATEGORY_MAPPINGS.get(topic.strip().lower(), topic.strip())

        if mapped_topic not in SECTIONAL_PROMPTS:
            return jsonify({'error': f"Invalid topic. Available: {list(SECTIONAL_PROMPTS.keys())}"}), 400

        count = data.get('count', 1)
        if not isinstance(count, int) or not (1 <= count <= 5):
            return jsonify({'error': 'Count must be an integer between 1 and 5'}), 400

        sections = generate_study_material(mapped_topic, count)
        if not sections:
            return jsonify({'error': 'Generation failed'}), 500

        structured = parse_mcqs(sections[0])
        if not structured:
            print("\n[DEBUG] Raw output:\n", sections[0])
            return jsonify({'error': 'Parsing failed: MCQ format not recognized.'}), 500

        # Parse answer key from the same content
        answer_key = parse_answer_key(sections[0])
        if not answer_key:
            print("[DEBUG] No answer key found, generating from questions")
            # Fallback: generate answer key from parsed questions
            answer_key = []
            for question in structured:
                answer_key.append({
                    "question": question['id'],
                    "answer": chr(65 + question['correct']),
                    "answer_index": question['correct']
                })

        return jsonify({
            'success': True,
            'topic': topic,
            'mapped_topic': mapped_topic,
            'count': len(structured),
            'test': structured,
            'answer_key': answer_key,
            'timestamp': datetime.now().isoformat(),
            'service': 'sectional_tests'
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    """Download test as PDF"""
    try:
        data = request.get_json()
        topic = data.get('topic') or data.get('subcategory')
        if topic:
            topic = topic.replace("-", " ").title()
        else:
            return jsonify({'error': 'Topic is missing'}), 400

        count = data.get('count', 1)
        if topic not in SECTIONAL_PROMPTS:
            return jsonify({'error': f"Invalid topic. Available: {list(SECTIONAL_PROMPTS.keys())}"}), 400
        if not isinstance(count, int) or not (1 <= count <= 5):
            return jsonify({'error': 'Count must be an integer between 1 and 5'}), 400

        sections = generate_study_material(topic, count)
        if not sections:
            return jsonify({'error': 'Failed to generate content'}), 500

        pdf_buffer = create_pdf(sections, f"{topic} Practice Set")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_buffer.getvalue())
            tmp_path = tmp.name

        filename = f"{topic.lower().replace(' ', '_')}_clat_practice.pdf"
        return send_file(tmp_path, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/download-answer-key', methods=['POST'])
def download_answer_key():
    """Download answer key as PDF"""
    try:
        data = request.get_json()
        questions = data.get('questions', [])
        answer_key = data.get('answer_key', [])
        test_metadata = data.get('test_metadata', {})
        
        if not questions or not answer_key:
            return jsonify({'error': 'Questions and answer key data are required'}), 400

        pdf_buffer = create_answer_key_pdf(questions, answer_key, test_metadata)
        if not pdf_buffer:
            return jsonify({'error': 'Failed to create answer key PDF'}), 500

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_buffer.getvalue())
            tmp_path = tmp.name

        filename = f"Answer_Key_{test_metadata.get('sectionName', 'Test')}_{test_metadata.get('subcategoryName', 'Practice')}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        return send_file(tmp_path, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route("/topics", methods=['GET'])
def get_topics():
    """Get all available topics"""
    return jsonify({
        'topics': list(SECTIONAL_PROMPTS.keys()),
        'count': len(SECTIONAL_PROMPTS),
        'descriptions': {
            'Critical Reasoning': 'Logical argument analysis',
            'General Knowledge': 'Current affairs & static',
            'Legal Reasoning': 'Legal principles and reasoning',
            'Mathematics': 'Quantitative aptitude',
            'Reading Comprehension': 'Abstract and inference-based RC'
        },
        'service': 'sectional_tests'
    })

@app.route("/api/generate-practice", methods=["POST"])
def generate_practice():
    """Generate practice questions"""
    try:
        data = request.get_json()
        section = data.get("section")
        subcategory = data.get("subcategory")
        passages = data.get("passages", 1)
        if not section or not subcategory:
            return jsonify({"error": "Section and subcategory are required"}), 400
        # Use the mapping to convert frontend subcategory to backend topic
        topic_name = SUBCATEGORY_MAPPINGS.get(subcategory)
        if not topic_name:
            return jsonify({"error": f"Unsupported subcategory: {subcategory}"}), 400
        if topic_name not in SECTIONAL_PROMPTS:
            return jsonify({"error": f"Unsupported topic: {topic_name}"}), 400
        print(f"[API] Generating practice for {topic_name} (subcategory: {subcategory}) with {passages} passages")
        generated = generate_study_material(topic_name, passages)
        if not generated:
            return jsonify({"error": "Content generation failed"}), 500
        all_questions = []
        for p_index, raw in enumerate(generated):
            print(f"[API] Processing passage {p_index + 1}")
            questions = parse_mcqs(raw)
            for q_index, q in enumerate(questions):
                all_questions.append({
                    "passageIndex": p_index,
                    "id": f"{p_index}-{q_index}",
                    "passage": q["passage"],
                    "question": q["question"],
                    "options": q["options"],
                    "correct": q["correct"],
                    "explanation": q["explanation"]
                })
        print(f"[API] Generated {len(all_questions)} total questions")
        return jsonify({
            "success": True,
            "questions": all_questions,
            "total": len(all_questions),
            "service": "sectional_tests"
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500

# Test parser endpoint
@app.route('/test-parser', methods=['GET'])
def test_parser():
    """Test the MCQ parser with sample data"""
    sample_text = """
This is a sample passage about legal reasoning and constitutional law principles.

**MCQs**

1. What is the primary function of the Constitution?
(A) To establish government structure
(B) To define citizen rights only
(C) To create laws for states
(D) To manage international relations
Answer: (A)
Explanation: The Constitution establishes the basic structure of government and defines the relationship between different organs of the state.

2. Which article deals with Right to Equality?
(A) Article 19
(B) Article 14
(C) Article 21
(D) Article 32
Answer: (B)
Explanation: Article 14 of the Indian Constitution guarantees the Right to Equality before law.
"""
    
    result = parse_mcqs(sample_text)
    return jsonify({
        'success': True,
        'parsed_questions': result,
        'count': len(result),
        'sample_input': sample_text
    })

# =============================================================================
# HEALTH CHECK ROUTES
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check for all services"""
    return jsonify({
        'status': 'healthy',
        'message': 'All CLAT services are running',
        'services': {
            'gk_research': 'operational',
            'lexa_chatbot': 'operational', 
            'qt_mentor': 'operational',
            'sectional_tests': 'operational'
        },
        'groq_configured': bool(GROQ_API_KEY),
        'timestamp': datetime.now().isoformat(),
        'available_topics': {
            'gk_topics': list(TOPIC_CONTEXTS.keys()),
            'qt_topics': list(QT_TOPIC_MAPPING.keys()),
            'sectional_topics': list(SECTIONAL_PROMPTS.keys())
        }
    })

# Legacy health endpoints for backward compatibility
@app.route('/gk/health', methods=['GET'])
def gk_health_check():
    """Health check for GK Research Engine"""
    return jsonify({
        'status': 'healthy',
        'service': 'gk_research',
        'pdf_processing_available': PDF_PROCESSING_AVAILABLE,
        'groq_api_available': bool(GROQ_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/gk/test-pdf', methods=['GET'])
def test_pdf_processing():
    """Test PDF processing capability"""
    try:
        if not PDF_PROCESSING_AVAILABLE:
            return jsonify({
                'status': 'error',
                'message': 'PDF processing not available',
                'pdf_processing_available': False,
                'error_details': 'PyMuPDF library is not properly installed or accessible'
            }), 400
        
        # Test if we can create a simple PDF and extract text
        import tempfile
        import os
        
        # Create a simple test PDF
        test_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF'
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(test_pdf_content)
            temp_file_path = temp_file.name
        
        try:
            # Test PDF processing
            doc = fitz.open(temp_file_path)
            text_content = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_content += page.get_text()
            doc.close()
            
            # Clean up
            os.unlink(temp_file_path)
            
            return jsonify({
                'status': 'success',
                'message': 'PDF processing is working correctly',
                'pdf_processing_available': True,
                'test_result': 'Successfully extracted text from test PDF',
                'extracted_text': text_content[:100] + '...' if len(text_content) > 100 else text_content
            })
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise e
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'PDF processing test failed',
            'pdf_processing_available': PDF_PROCESSING_AVAILABLE,
            'error_details': str(e)
        }), 500

@app.route('/lexa/health', methods=['GET'])
def lexa_health_check():
    """Lexa Chatbot health check"""
    return jsonify({
        "status": "healthy", 
        "message": "CLAT Chatbot API is running",
        "service": "lexa_chatbot",
        "timestamp": datetime.now().isoformat()
    })

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "api_info": "/status",
            "gk_research": ["/gk/generate", "/gk/topics", "/gk/assistant", "/gk/upload-pdf", "/gk/health"],
            "lexa_chatbot": ["/lexa/chat", "/lexa/health"],
            "qt_mentor": ["/qt/generate-question", "/qt/test"],
            "sectional_tests": ["/generate-test", "/download-pdf", "/topics", "/api/generate-practice"],
            "health": "/health",
            "debug": "/test-parser"
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on the server"
    }), 500

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    # Check if API key is set
    if not GROQ_API_KEY:
        print("Warning: GROQ_API_KEY not set!")
    
    print("=" * 80)
    print("🚀 Starting CLAT Unified API Server v2.0.1 - FIXED")
    print("=" * 80)
    print(f"📍 Server URL: http://127.0.0.1:{PORT}")
    print(f"🔗 Main endpoint: http://127.0.0.1:{PORT}/")
    print("")
    print("📚 GK Research Engine:")
    print(f"   • Generate: http://127.0.0.1:{PORT}/gk/generate")
    print(f"   • Assistant: http://127.0.0.1:{PORT}/gk/assistant")
    print(f"   • Topics: http://127.0.0.1:{PORT}/gk/topics")
    print("")
    print("🤖 Lexa Chatbot:")
    print(f"   • Chat: http://127.0.0.1:{PORT}/lexa/chat")
    print("")
    print("🔢 QT Mentor:")
    print(f"   • Generate: http://127.0.0.1:{PORT}/qt/generate-question")
    print(f"   • Test: http://127.0.0.1:{PORT}/qt/test")
    print("")
    print("📝 Sectional Tests:")
    print(f"   • Generate: http://127.0.0.1:{PORT}/generate-test")
    print(f"   • Download PDF: http://127.0.0.1:{PORT}/download-pdf")
    print(f"   • Topics: http://127.0.0.1:{PORT}/topics")
    print(f"   • Practice: http://127.0.0.1:{PORT}/api/generate-practice")
    print("")
    print("🔧 Debug:")
    print(f"   • Test Parser: http://127.0.0.1:{PORT}/test-parser")
    print("")
    print(f"❤️  Health Check: http://127.0.0.1:{PORT}/health")
    print("=" * 80)
    print(f"Groq API configured: {'Yes' if GROQ_API_KEY else 'No'}")
    print(f"GK Topics available: {len(TOPIC_CONTEXTS)}")
    print(f"QT Topics available: {len(QT_TOPIC_MAPPING)}")
    print(f"Sectional Topics available: {len(SECTIONAL_PROMPTS)}")
    print("=" * 80)

    if __name__ == "__main__":
        app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

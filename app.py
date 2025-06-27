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
- Format: "1.1 – (B) [detailed explanation with calculations, the explanation should be as if youre explaining to a 5 year old, and it should be lengthy, simple to understand ]"
- Include mathematical calculations where applicable
- Be thorough in explanations, almost like explainaing to a child, and be lengthy, i need 100 word explanations.

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

# Fixed Sectional Test Generator Prompts with consistent formatting
SECTIONAL_PROMPTS = {
    "Reading Comprehension": """
You are a CLAT Reading Comprehension test generator.
Generate a passage of 500–600 words in a formal academic tone.
The passage should contain logical arguments, assumptions, and analytical content.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5).
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of why it is correct.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly. Do not include any other headings.
""",
    
    "Grammar": """
You are a CLAT English Grammar test generator.
Generate a passage of 300-400 words with grammatical concepts and examples.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing grammar rules.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the grammar rule.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Vocabulary": """
You are a CLAT Vocabulary test generator.
Generate a passage of 300-400 words with advanced vocabulary words in context.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing vocabulary and word meanings.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the word meaning.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Para Jumbles": """
You are a CLAT Para Jumbles test generator.
Generate a passage explaining para jumble concepts and provide examples.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) with para jumble exercises.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the correct sequence.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Critical Reasoning": """
You are a CLAT Critical Reasoning test generator.
Generate a passage of 400-500 words with logical arguments and reasoning scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing critical reasoning skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the reasoning.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Logical Reasoning": """
You are a CLAT Logical Reasoning test generator.
Generate a passage of 400-500 words with logical scenarios and reasoning problems.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing logical reasoning.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the logic.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Analytical Reasoning": """
You are a CLAT Analytical Reasoning test generator.
Generate a passage of 400-500 words with analytical scenarios and data.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing analytical reasoning.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the analysis.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Puzzles": """
You are a CLAT Puzzles test generator.
Generate a passage of 300-400 words explaining puzzle-solving techniques.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) with puzzle problems.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the solution.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Syllogisms": """
You are a CLAT Syllogisms test generator.
Generate a passage of 300-400 words explaining syllogistic reasoning.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) with syllogism problems.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the syllogistic reasoning.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Legal Reasoning": """
You are a CLAT Legal Reasoning test generator.
Generate a legal scenario passage of 400-500 words with legal principles and cases.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing legal reasoning.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the legal principle.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Constitutional Law": """
You are a CLAT Constitutional Law test generator.
Generate a passage of 400-500 words about constitutional principles and articles.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing constitutional law knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the constitutional provision.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Contract Law": """
You are a CLAT Contract Law test generator.
Generate a passage of 400-500 words about contract law principles and cases.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing contract law knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the contract law principle.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Tort Law": """
You are a CLAT Tort Law test generator.
Generate a passage of 400-500 words about tort law principles and cases.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing tort law knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the tort law principle.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Criminal Law": """
You are a CLAT Criminal Law test generator.
Generate a passage of 400-500 words about criminal law principles and cases.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing criminal law knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the criminal law principle.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Legal Principles": """
You are a CLAT Legal Principles test generator.
Generate a passage of 400-500 words about fundamental legal principles.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing legal principles knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the legal principle.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Legal Maxims": """
You are a CLAT Legal Maxims test generator.
Generate a passage of 300-400 words about important legal maxims and their applications.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing legal maxims knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the legal maxim.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Arithmetic": """
You are a CLAT Arithmetic test generator.
Generate a passage of 300-400 words with arithmetic problems and scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing arithmetic skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the calculation.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Algebra": """
You are a CLAT Algebra test generator.
Generate a passage of 300-400 words with algebraic problems and scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing algebra skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the algebraic solution.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Geometry": """
You are a CLAT Geometry test generator.
Generate a passage of 300-400 words with geometric problems and scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing geometry skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the geometric solution.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Data Interpretation": """
You are a CLAT Data Interpretation test generator.
Generate a passage of 400-500 words with data tables, charts, and interpretation scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing data interpretation skills.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the data interpretation.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Percentages": """
You are a CLAT Percentages test generator.
Generate a passage of 300-400 words with percentage problems and scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing percentage calculations.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the percentage calculation.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Profit & Loss": """
You are a CLAT Profit & Loss test generator.
Generate a passage of 300-400 words with profit and loss problems and business scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing profit and loss calculations.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the profit/loss calculation.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "General Knowledge": """
You are a CLAT General Knowledge test generator.
Generate a passage of 500-600 words about current affairs and general knowledge topics.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing general knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the fact.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Current Affairs": """
You are a CLAT Current Affairs test generator.
Generate a passage of 500-600 words about recent current affairs and developments.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing current affairs knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the current affair.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "History": """
You are a CLAT History test generator.
Generate a passage of 400-500 words about historical events and developments.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing history knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the historical fact.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Geography": """
You are a CLAT Geography test generator.
Generate a passage of 400-500 words about geographical features and concepts.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing geography knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the geographical concept.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (A)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Politics": """
You are a CLAT Politics test generator.
Generate a passage of 400-500 words about political systems and developments.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing political knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the political concept.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Economics": """
You are a CLAT Economics test generator.
Generate a passage of 400-500 words about economic concepts and developments.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing economics knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the economic concept.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Science & Technology": """
You are a CLAT Science & Technology test generator.
Generate a passage of 400-500 words about scientific and technological developments.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing science and technology knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the scientific concept.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Sports": """
You are a CLAT Sports test generator.
Generate a passage of 300-400 words about sports events and achievements.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing sports knowledge.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the sports fact.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Ratios": """
You are a CLAT Ratios test generator.
Generate a passage of 300-400 words with ratio and proportion problems and scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing ratio and proportion calculations.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the ratio calculation.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (B)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Averages": """
You are a CLAT Averages test generator.
Generate a passage of 300-400 words with average problems and scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing average calculations.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the average calculation.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (C)
Explanation: Explanation text here.

Follow this format exactly.
""",
    
    "Compound Interest": """
You are a CLAT Compound Interest test generator.
Generate a passage of 300-400 words with compound interest problems and banking scenarios.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5) testing compound interest calculations.
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of the compound interest calculation.

Structure:
1. Question text here?
(A) Option 1 text
(B) Option 2 text
(C) Option 3 text
(D) Option 4 text
Answer: (D)
Explanation: Explanation text here.

Follow this format exactly.
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

    # Logical
    "assumptions": "Critical Reasoning",
    "inferences": "Critical Reasoning",
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
    "dividing-quantities-in-given-ratios": "Ratios",
    "missing-values-based-on-ratios": "Ratios",
    "simplification-of-numbers-to-derive-simplest-ratio": "Ratios",
    "simple-and-weighted-averages": "Averages",
    "cost-price-selling-price-and-marked-price-calculations": "Profit & Loss",
    "discount-profit-loss": "Profit & Loss",
    "basic-formula-applications-of-simple-and-compound-interest": "Compound Interest",
    "area-perimeter-volume-and-surface-area": "Geometry",
    # Add direct mappings for single-subcategory cases
    "general-legal": "Legal Reasoning",
    "general-gk": "General Knowledge",
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

def generate_study_material(topic, count):
    """Generate study material for sectional tests"""
    all_sections = []
    for i in range(count):
        print(f"📝 Generating section {i+1}/{count} for {topic}...")
        mapped_topic = SUBCATEGORY_MAPPINGS.get(topic or "", topic or "")
        prompt = SECTIONAL_PROMPTS.get(mapped_topic, f"Generate a CLAT-level {mapped_topic} test with passage, questions, and answer key.")

        messages = [
            {"role": "system", "content": "You are an expert CLAT study material generator."},
            {"role": "user", "content": prompt}
        ]
        result = call_groq_api(messages)
        if result:
            all_sections.append(f"Topic: {topic}\n\n{result.strip()}")
        else:
            print(f"❌ Failed to generate section {i+1}")
    return all_sections

def parse_mcqs(raw_text):
    """Parse MCQs from raw text - FIXED VERSION"""
    try:
        parts = re.split(r'\*\*MCQs\*\*', raw_text)
        if len(parts) < 2:
            print("[DEBUG] No **MCQs** section found")
            return []

        passage = parts[0].strip()
        mcqs_text = parts[1].strip()

        # Updated regex to match the actual format from prompts
        question_blocks = re.findall(r'(\d+\..*?)(?=\n\d+\.|\Z)', mcqs_text, re.DOTALL)
        structured_questions = []

        print(f"[DEBUG] Found {len(question_blocks)} question blocks")

        for idx, block in enumerate(question_blocks, start=1):
            try:
                # Look for question text before first option (A)
                q_match = re.search(r'\d+\.\s*(.+?)\n\(A\)', block, re.DOTALL)
                question = q_match.group(1).strip() if q_match else "Unknown question"

                options = []
                for opt in ['A', 'B', 'C', 'D']:
    # Match: (A) Option text until the next (B)/(C)/(D)/Answer/End
                    opt_match = re.search(rf'\({opt}\)\s*(.+?)(?=\n\([A-D]\)|\nAnswer:|\Z)', block, re.DOTALL)
                    if opt_match:
                        options.append(opt_match.group(1).strip())
                    else:
                        options.append(f"Option ({opt}) text missing")



                # Look for answer in format Answer: (A)
                ans_match = re.search(r'Answer:\s*(([A-D]))', block)
                correct_letter = ans_match.group(1) if ans_match else 'A'
                correct_index = ord(correct_letter) - ord('A')

                # Look for explanation
                exp_match = re.search(r'Explanation:\s*(.+)', block, re.DOTALL)
                explanation = exp_match.group(1).strip() if exp_match else "Explanation not available"

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

def create_pdf(contents, title):
    """Create PDF from content"""
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
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln()
    for section in contents:
        try:
            clean = section.encode('latin1', 'replace').decode('latin1')
        except:
            clean = section
        pdf.multi_cell(0, 10, clean)
        pdf.ln()
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
        
        print(f"GK Generated response length: {len(response)} characters")
        
        return jsonify({
            'response': response,
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
        return jsonify({
            'response': response,
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
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file.filename or not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        # For now, return a placeholder response since PyMuPDF isn't imported
        return jsonify({
            'error': 'PDF processing not available in this version',
            'message': 'Please use text input instead'
        }), 400

    except Exception as e:
        print(f"PDF upload error: {e}")
        return jsonify({'error': 'Server error processing PDF'}), 500

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
        return jsonify({
            "response": response,
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
        # Basic validation of generated content
        if not validate_qt_content(response):
            print("QT Content validation failed")
            return jsonify({
                "success": False,
                "error": "Generated content doesn't meet quality standards",
                "details": "Please try generating again",
                "service": "qt_mentor"
            }), 400
        return jsonify({
            "success": True,
            "rawOutput": response,
            "topic": topic,
            "contentLength": len(response),
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
    """Generate sectional test content"""
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

        return jsonify({
            'success': True,
            'topic': topic,
            'mapped_topic': mapped_topic,
            'count': len(structured),
            'test': structured,
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
    """GK Research Engine health check"""
    return jsonify({
        'status': 'healthy', 
        'message': 'GK Research Engine API is running',
        'service': 'gk_research',
        'groq_configured': bool(GROQ_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

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

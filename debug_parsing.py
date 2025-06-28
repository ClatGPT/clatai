#!/usr/bin/env python3
"""
Debug script to test MCQ parsing and AI response format
"""

import requests
import json
import re

def test_ai_response_format():
    """Test the actual AI response format to see what's being generated"""
    
    print("🔍 Testing AI Response Format")
    print("=" * 60)
    
    # Test with a simple topic
    test_data = {
        "topic": "Reading Comprehension",
        "count": 1
    }
    
    try:
        print("📡 Making request to generate content...")
        response = requests.post(
            "http://localhost:5000/generate-test",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Request successful!")
            print(f"📊 Test count: {data.get('count', 0)}")
            print(f"🔑 Answer key count: {len(data.get('answer_key', []))}")
            
            if data.get('test'):
                print(f"📝 Questions generated: {len(data['test'])}")
                # Show first question structure
                first_q = data['test'][0]
                print(f"📋 First question structure: {list(first_q.keys())}")
            else:
                print("❌ No questions in response")
                
        elif response.status_code == 500:
            print("❌ Server error - checking response...")
            try:
                error_data = response.json()
                print(f"📄 Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"📄 Raw error: {response.text[:500]}...")
        else:
            print(f"❌ HTTP {response.status_code}")
            print(f"📄 Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_mcq_parsing():
    """Test the MCQ parsing function with sample data"""
    
    print(f"\n\n🔍 Testing MCQ Parsing Function")
    print("=" * 60)
    
    # Test the parse_mcqs function directly
    sample_text = """
This is a sample passage about reading comprehension and critical thinking skills.

**MCQs**

1. What is the main purpose of reading comprehension?
(A) To memorize facts
(B) To understand and analyze text
(C) To speed read quickly
(D) To skip difficult parts
Answer: (B)
Explanation: Reading comprehension is primarily about understanding and analyzing the content of a text, not just memorizing facts or reading quickly.

2. Which skill is most important for critical reading?
(A) Memorization
(B) Analysis and evaluation
(C) Speed reading
(D) Guessing
Answer: (B)
Explanation: Critical reading requires analysis and evaluation of the text, including understanding arguments, identifying assumptions, and evaluating evidence.

**ANSWER KEY**
1. (B)
2. (B)
"""
    
    print("📝 Testing with sample text:")
    print(sample_text)
    print("\n" + "="*60)
    
    # Test the parsing logic
    try:
        parts = re.split(r'\*\*MCQs\*\*', sample_text)
        print(f"📊 Parts after splitting: {len(parts)}")
        
        if len(parts) >= 2:
            passage = parts[0].strip()
            mcqs_text = parts[1].strip()
            
            print(f"📖 Passage length: {len(passage)} chars")
            print(f"📝 MCQs text length: {len(mcqs_text)} chars")
            print(f"📝 MCQs text preview: {mcqs_text[:200]}...")
            
            # Test question block extraction
            question_blocks = re.findall(r'(\d+\..*?)(?=\n\d+\.|\Z)', mcqs_text, re.DOTALL)
            print(f"🔢 Found {len(question_blocks)} question blocks")
            
            for i, block in enumerate(question_blocks):
                print(f"\n📋 Question {i+1} block:")
                print(f"   Length: {len(block)} chars")
                print(f"   Preview: {block[:100]}...")
                
                # Test question extraction
                q_match = re.search(r'\d+\.\s*(.+?)\n\(A\)', block, re.DOTALL)
                if q_match:
                    question = q_match.group(1).strip()
                    print(f"   ✅ Question extracted: {question[:50]}...")
                else:
                    print(f"   ❌ Question extraction failed")
                
                # Test options extraction
                options = []
                for opt in ['A', 'B', 'C', 'D']:
                    opt_match = re.search(rf'\({opt}\)\s*(.+?)(?=\n\([A-D]\)|\nAnswer:|\Z)', block, re.DOTALL)
                    if opt_match:
                        options.append(opt_match.group(1).strip())
                    else:
                        options.append(f"Option ({opt}) text missing")
                
                print(f"   📝 Options: {[opt[:30] + '...' if len(opt) > 30 else opt for opt in options]}")
                
                # Test answer extraction
                ans_match = re.search(r'Answer:\s*\(([A-D])\)', block)
                if ans_match:
                    correct_letter = ans_match.group(1)
                    print(f"   ✅ Answer: {correct_letter}")
                else:
                    print(f"   ❌ Answer extraction failed")
                
                # Test explanation extraction
                exp_match = re.search(r'Explanation:\s*(.+)', block, re.DOTALL)
                if exp_match:
                    explanation = exp_match.group(1).strip()
                    print(f"   ✅ Explanation: {explanation[:50]}...")
                else:
                    print(f"   ❌ Explanation extraction failed")
        else:
            print("❌ No **MCQs** section found in sample text")
            
    except Exception as e:
        print(f"❌ Error in parsing test: {e}")

def test_groq_api_directly():
    """Test the Groq API directly to see what format it returns"""
    
    print(f"\n\n🔍 Testing Groq API Directly")
    print("=" * 60)
    
    try:
        # Test the test-parser endpoint which should show us the raw format
        response = requests.get("http://localhost:5000/test-parser", timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Test parser successful!")
            print(f"📊 Parsed questions: {data.get('count', 0)}")
            
            if data.get('parsed_questions'):
                print(f"📝 Sample parsed question structure:")
                first_q = data['parsed_questions'][0]
                for key, value in first_q.items():
                    if key == 'passage':
                        print(f"   {key}: {value[:100]}...")
                    elif key == 'explanation':
                        print(f"   {key}: {value[:100]}...")
                    else:
                        print(f"   {key}: {value}")
            else:
                print("❌ No parsed questions returned")
                
            print(f"\n📄 Sample input used:")
            sample_input = data.get('sample_input', '')
            print(sample_input[:500] + "..." if len(sample_input) > 500 else sample_input)
        else:
            print(f"❌ Test parser failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing Groq API: {e}")

if __name__ == "__main__":
    print("🚀 Starting MCQ Parsing Debug")
    print("=" * 80)
    
    # Test the test parser first
    test_groq_api_directly()
    
    # Test MCQ parsing with sample data
    test_mcq_parsing()
    
    # Test actual AI response
    test_ai_response_format()
    
    print(f"\n\n✅ Debug Complete!")
    print("=" * 80) 
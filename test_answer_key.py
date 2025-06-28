#!/usr/bin/env python3
"""
Test script for answer key PDF generation
"""

import requests
import json

# Test data
test_questions = [
    {
        "id": "1",
        "passage": "This is a test passage about legal reasoning.",
        "question": "What is the primary function of the Constitution?",
        "options": [
            "To establish government structure",
            "To define citizen rights only", 
            "To create laws for states",
            "To manage international relations"
        ],
        "correct": 0,
        "explanation": "The Constitution establishes the basic structure of government and defines the relationship between different organs of the state."
    },
    {
        "id": "2", 
        "passage": "This is a test passage about legal reasoning.",
        "question": "Which article deals with Right to Equality?",
        "options": [
            "Article 19",
            "Article 14",
            "Article 21", 
            "Article 32"
        ],
        "correct": 1,
        "explanation": "Article 14 of the Indian Constitution guarantees the Right to Equality before law."
    }
]

test_answer_key = [
    {
        "question": "1",
        "answer": "A",
        "answer_index": 0
    },
    {
        "question": "2", 
        "answer": "B",
        "answer_index": 1
    }
]

test_metadata = {
    "sectionName": "Legal Reasoning",
    "subcategoryName": "Constitutional Law",
    "passages": 1
}

def test_answer_key_generation():
    """Test the answer key PDF generation endpoint"""
    
    # Test data
    payload = {
        "questions": test_questions,
        "answer_key": test_answer_key,
        "test_metadata": test_metadata
    }
    
    try:
        # Make request to the answer key endpoint
        response = requests.post(
            "http://localhost:5000/download-answer-key",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Save the PDF file
            with open("test_answer_key.pdf", "wb") as f:
                f.write(response.content)
            print("✅ Answer key PDF generated successfully!")
            print("📄 Saved as: test_answer_key.pdf")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the Flask server is running on localhost:5000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_test_generation():
    """Test the test generation endpoint"""
    
    payload = {
        "section": "legal-reasoning",
        "subcategory": "constitutional-law", 
        "passages": 1
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/generate-test",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nTest Generation Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Test generated successfully!")
            print(f"📊 Questions: {len(data.get('test', []))}")
            print(f"🔑 Answer Key: {len(data.get('answer_key', []))}")
            
            # Test answer key generation with the generated data
            if data.get('test') and data.get('answer_key'):
                print("\n🔄 Testing answer key PDF generation with generated data...")
                test_with_generated_data(data['test'], data['answer_key'])
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the Flask server is running on localhost:5000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_with_generated_data(questions, answer_key):
    """Test answer key PDF with generated data"""
    
    payload = {
        "questions": questions,
        "answer_key": answer_key,
        "test_metadata": {
            "sectionName": "Generated Test",
            "subcategoryName": "Generated Subcategory",
            "passages": 1
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/download-answer-key",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            with open("generated_answer_key.pdf", "wb") as f:
                f.write(response.content)
            print("✅ Generated answer key PDF created successfully!")
            print("📄 Saved as: generated_answer_key.pdf")
        else:
            print(f"❌ Error generating PDF: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Answer Key PDF Generation")
    print("=" * 50)
    
    # Test with sample data
    test_answer_key_generation()
    
    # Test with generated data
    test_test_generation()
    
    print("\n✅ Testing complete!") 
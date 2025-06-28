#!/usr/bin/env python3
"""
Test script to verify practice-online.html and sectional test generation fixes
"""

import requests
import json

def test_practice_generation():
    """Test the practice generation endpoint with different sections"""
    
    test_cases = [
        {
            "section": "legal",
            "subcategory": "general-legal",
            "passages": 1,
            "description": "Legal Reasoning - General Legal"
        },
        {
            "section": "gk", 
            "subcategory": "general-gk",
            "passages": 1,
            "description": "General Knowledge - General GK"
        },
        {
            "section": "english",
            "subcategory": "main-idea",
            "passages": 1,
            "description": "English - Main Idea"
        },
        {
            "section": "logical",
            "subcategory": "assumptions",
            "passages": 1,
            "description": "Logical - Assumptions"
        },
        {
            "section": "quantitative",
            "subcategory": "percentage-comparison",
            "passages": 1,
            "description": "Quantitative - Percentage Comparison"
        }
    ]
    
    print("🧪 Testing Practice Generation Fixes")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['description']}")
        print(f"   Section: {test_case['section']}")
        print(f"   Subcategory: {test_case['subcategory']}")
        print(f"   Passages: {test_case['passages']}")
        
        try:
            response = requests.post(
                "http://localhost:5000/api/generate-practice",
                json=test_case,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('questions'):
                    print(f"   ✅ SUCCESS: Generated {len(data['questions'])} questions")
                    print(f"   📊 Total: {data.get('total', 0)} questions")
                    
                    # Check if questions have proper structure
                    first_question = data['questions'][0]
                    required_fields = ['id', 'passage', 'question', 'options', 'correct', 'explanation']
                    missing_fields = [field for field in required_fields if field not in first_question]
                    
                    if missing_fields:
                        print(f"   ⚠️  WARNING: Missing fields in question: {missing_fields}")
                    else:
                        print(f"   ✅ Question structure is correct")
                        print(f"   📝 Sample question: {first_question['question'][:50]}...")
                else:
                    print(f"   ❌ FAILED: No questions generated")
                    print(f"   📄 Response: {data}")
            else:
                print(f"   ❌ FAILED: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   📄 Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   📄 Error: {response.text[:100]}...")
                    
        except requests.exceptions.ConnectionError:
            print("   ❌ CONNECTION ERROR: Make sure Flask server is running on localhost:5000")
        except requests.exceptions.Timeout:
            print("   ❌ TIMEOUT: Request took too long")
        except Exception as e:
            print(f"   ❌ UNEXPECTED ERROR: {e}")

def test_sectional_test_generation():
    """Test the sectional test generation endpoint"""
    
    print(f"\n\n🧪 Testing Sectional Test Generation")
    print("=" * 60)
    
    test_cases = [
        {
            "topic": "general-legal",
            "count": 1,
            "description": "Legal Reasoning Test"
        },
        {
            "topic": "general-gk", 
            "count": 1,
            "description": "General Knowledge Test"
        },
        {
            "topic": "main-idea",
            "count": 1,
            "description": "Reading Comprehension Test"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['description']}")
        print(f"   Topic: {test_case['topic']}")
        print(f"   Count: {test_case['count']}")
        
        try:
            response = requests.post(
                "http://localhost:5000/generate-test",
                json=test_case,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('test'):
                    print(f"   ✅ SUCCESS: Generated {len(data['test'])} questions")
                    print(f"   📊 Count: {data.get('count', 0)} questions")
                    print(f"   🔑 Answer Key: {len(data.get('answer_key', []))} entries")
                    
                    # Check if test has proper structure
                    first_question = data['test'][0]
                    required_fields = ['id', 'passage', 'question', 'options', 'correct', 'explanation']
                    missing_fields = [field for field in required_fields if field not in first_question]
                    
                    if missing_fields:
                        print(f"   ⚠️  WARNING: Missing fields in question: {missing_fields}")
                    else:
                        print(f"   ✅ Question structure is correct")
                        print(f"   📝 Sample question: {first_question['question'][:50]}...")
                else:
                    print(f"   ❌ FAILED: No test generated")
                    print(f"   📄 Response: {data}")
            else:
                print(f"   ❌ FAILED: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   📄 Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   📄 Error: {response.text[:100]}...")
                    
        except requests.exceptions.ConnectionError:
            print("   ❌ CONNECTION ERROR: Make sure Flask server is running on localhost:5000")
        except requests.exceptions.Timeout:
            print("   ❌ TIMEOUT: Request took too long")
        except Exception as e:
            print(f"   ❌ UNEXPECTED ERROR: {e}")

def test_health_check():
    """Test the health check endpoint"""
    
    print(f"\n\n🏥 Testing Health Check")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:5000/health", timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check: {data.get('status', 'unknown')}")
            print(f"📊 Services: {data.get('services', {})}")
            print(f"🔑 GROQ Configured: {data.get('groq_configured', False)}")
            print(f"📚 Available Topics: {len(data.get('available_topics', {}).get('sectional_topics', []))}")
        else:
            print(f"❌ Health Check Failed: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR: Make sure Flask server is running on localhost:5000")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    print("🚀 Starting Practice and Sectional Test Fix Verification")
    print("=" * 80)
    
    # Test health check first
    test_health_check()
    
    # Test practice generation
    test_practice_generation()
    
    # Test sectional test generation
    test_sectional_test_generation()
    
    print(f"\n\n✅ Testing Complete!")
    print("=" * 80)
    print("📝 Summary:")
    print("   • If all tests pass, the fixes are working correctly")
    print("   • If any test fails, check the error messages above")
    print("   • Make sure your Flask server is running: python app.py") 
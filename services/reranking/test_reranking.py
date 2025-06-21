#!/usr/bin/env python3
"""
Test script for the custom reranking service.
"""

import requests
import time

def test_health_check(base_url="http://localhost:8765"):
    """Test the health check endpoints."""
    print("Testing health check endpoints...")
    
    # Test basic health
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test ready check
    try:
        response = requests.get(f"{base_url}/v1/health/ready")
        print(f"Ready check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Ready check failed: {e}")

def test_ranking(base_url="http://localhost:8765"):
    """Test the ranking endpoint with sample data."""
    print("\nTesting ranking endpoint...")
    
    # Sample data similar to the NVIDIA NIM documentation
    test_data = {
        "model": "custom-reranker",
        "query": {"text": "which way should i go?"},
        "passages": [
            {"text": "two roads diverged in a yellow wood, and sorry i could not travel both and be one traveler, long i stood and looked down one as far as i could to where it bent in the undergrowth;"},
            {"text": "then took the other, as just as fair, and having perhaps the better claim because it was grassy and wanted wear, though as for that the passing there had worn them really about the same,"},
            {"text": "and both that morning equally lay in leaves no step had trodden black. oh, i marked the first for another day! yet knowing how way leads on to way i doubted if i should ever come back."},
            {"text": "i shall be telling this with a sigh somewhere ages and ages hence: two roads diverged in a wood, and i, i took the one less traveled by, and that has made all the difference."}
        ],
        "truncate": "END"
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/v1/ranking",
            headers={"Content-Type": "application/json"},
            json=test_data
        )
        end_time = time.time()
        
        print(f"Ranking request: {response.status_code}")
        print(f"Response time: {end_time - start_time:.3f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print("Rankings:")
            for i, ranking in enumerate(result["rankings"]):
                passage_idx = ranking["index"]
                logit = ranking["logit"]
                passage_text = test_data["passages"][passage_idx]["text"][:100] + "..."
                print(f"  {i+1}. Index {passage_idx} (logit: {logit:.3f}): {passage_text}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Ranking test failed: {e}")

def test_simple_ranking(base_url="http://localhost:8765"):
    """Test with a simple example."""
    print("\nTesting simple ranking...")
    
    simple_data = {
        "model": "custom-reranker",
        "query": {"text": "What is machine learning?"},
        "passages": [
            {"text": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data."},
            {"text": "The weather today is sunny and warm."},
            {"text": "Artificial intelligence and machine learning are transforming various industries."},
            {"text": "I like to eat pizza for dinner."}
        ],
        "truncate": "NONE"
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/ranking",
            headers={"Content-Type": "application/json"},
            json=simple_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print("Simple ranking results:")
            for i, ranking in enumerate(result["rankings"]):
                passage_idx = ranking["index"]
                logit = ranking["logit"]
                passage_text = simple_data["passages"][passage_idx]["text"]
                print(f"  {i+1}. Index {passage_idx} (logit: {logit:.3f}): {passage_text}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Simple ranking test failed: {e}")

def main():
    """Run all tests."""
    print("Custom Reranking Service Test")
    print("=" * 40)
    
    base_url = "http://localhost:8765"
    
    # Wait a moment for service to be ready
    print("Waiting for service to be ready...")
    time.sleep(2)
    
    test_health_check(base_url)
    test_ranking(base_url)
    test_simple_ranking(base_url)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()

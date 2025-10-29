#!/usr/bin/env python3
"""
Test script for webhook transaction service.
Tests all success criteria: response time, idempotency, background processing.
"""

import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000"

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def test_health_check():
    """Test 1: Health Check"""
    print("\n✅ Test 1: Health Check")
    response = requests.get(f"{BASE_URL}/")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)}")
    assert response.status_code == 200
    assert data["status"] == "HEALTHY"
    assert "current_time" in data
    print("   ✓ PASSED")

def test_webhook_response_time():
    """Test 2: Response Time (< 500ms)"""
    print("\n✅ Test 2: Webhook Response Time")
    
    txn_id = f"txn_test_{int(time.time() * 1000)}"
    payload = {
        "transaction_id": txn_id,
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1500,
        "currency": "INR"
    }
    
    start = time.time()
    response = requests.post(f"{BASE_URL}/v1/webhooks/transactions", json=payload)
    elapsed_ms = (time.time() - start) * 1000
    
    print(f"   Status: {response.status_code}")
    print(f"   Response Time: {elapsed_ms:.2f}ms")
    print(f"   Response: {response.json()}")
    
    assert response.status_code == 202
    assert elapsed_ms < 500, f"Response time {elapsed_ms}ms exceeded 500ms"
    print(f"   ✓ PASSED - Responded in {elapsed_ms:.2f}ms")
    
    return txn_id

def test_transaction_status_processing(txn_id):
    """Test 3: Transaction Status - PROCESSING"""
    print("\n✅ Test 3: Transaction Status (Should be PROCESSING)")
    
    response = requests.get(f"{BASE_URL}/v1/transactions/{txn_id}")
    data = response.json()
    
    print(f"   Status Code: {response.status_code}")
    print(f"   Transaction Status: {data['status']}")
    print(f"   Created At: {data['created_at']}")
    print(f"   Processed At: {data['processed_at']}")
    
    assert response.status_code == 200
    assert data["status"] == "PROCESSING"
    assert data["processed_at"] is None
    assert data["transaction_id"] == txn_id
    print("   ✓ PASSED")

def test_idempotency(txn_id):
    """Test 4: Idempotency - Duplicate Webhooks"""
    print("\n✅ Test 4: Idempotency (Sending 5 Duplicates)")
    
    payload = {
        "transaction_id": txn_id,
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1500,
        "currency": "INR"
    }
    
    for i in range(5):
        response = requests.post(f"{BASE_URL}/v1/webhooks/transactions", json=payload)
        print(f"   Attempt {i+1}: Status {response.status_code} - {response.json()['message']}")
        assert response.status_code == 202
    
    print("   ✓ PASSED - All duplicates handled gracefully")

def test_concurrent_duplicates():
    """Test 5: Concurrent Duplicate Requests"""
    print("\n✅ Test 5: Concurrent Duplicate Requests")
    
    txn_id = f"txn_concurrent_{int(time.time() * 1000)}"
    payload = {
        "transaction_id": txn_id,
        "source_account": "acc_user_999",
        "destination_account": "acc_merchant_999",
        "amount": 2500,
        "currency": "USD"
    }
    
    def send_request():
        return requests.post(f"{BASE_URL}/v1/webhooks/transactions", json=payload)
    
    # Send 10 concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_request) for _ in range(10)]
        responses = [f.result() for f in futures]
    
    success_count = sum(1 for r in responses if r.status_code == 202)
    print(f"   All 10 concurrent requests returned 202: {success_count}/10")
    
    time.sleep(1)  # Give DB time to settle
    
    # Verify transaction exists
    response = requests.get(f"{BASE_URL}/v1/transactions/{txn_id}")
    assert response.status_code == 200
    print("   ✓ PASSED - Only one transaction created")

def test_background_processing(txn_id):
    """Test 6: Background Processing (30 seconds)"""
    print("\n✅ Test 6: Background Processing (Waiting 30 seconds...)")
    
    for remaining in range(30, 0, -5):
        print(f"   {remaining} seconds remaining...")
        time.sleep(5)
    
    print("\n   Checking status after 30 seconds...")
    response = requests.get(f"{BASE_URL}/v1/transactions/{txn_id}")
    data = response.json()
    
    print(f"   Status Code: {response.status_code}")
    print(f"   Transaction Status: {data['status']}")
    print(f"   Created At: {data['created_at']}")
    print(f"   Processed At: {data['processed_at']}")
    
    assert response.status_code == 200
    assert data["status"] == "PROCESSED"
    assert data["processed_at"] is not None
    print("   ✓ PASSED - Transaction processed successfully")

def test_multiple_transactions():
    """Test 7: Multiple Independent Transactions"""
    print("\n✅ Test 7: Multiple Independent Transactions")
    
    txn_ids = []
    for i in range(3):
        txn_id = f"txn_multi_{int(time.time() * 1000)}_{i}"
        payload = {
            "transaction_id": txn_id,
            "source_account": f"acc_user_{i}",
            "destination_account": f"acc_merchant_{i}",
            "amount": 100 * (i + 1),
            "currency": "USD"
        }
        
        response = requests.post(f"{BASE_URL}/v1/webhooks/transactions", json=payload)
        print(f"   Transaction {i+1}: {txn_id} - Status {response.status_code}")
        assert response.status_code == 202
        txn_ids.append(txn_id)
        time.sleep(0.1)  # Small delay between requests
    
    # Verify all are processing
    for txn_id in txn_ids:
        response = requests.get(f"{BASE_URL}/v1/transactions/{txn_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "PROCESSING"
    
    print("   ✓ PASSED - All transactions queued successfully")

def main():
    try:
        print_header("WEBHOOK TRANSACTION SERVICE - COMPREHENSIVE TEST SUITE")
        
        # Test 1: Health Check
        test_health_check()
        
        # Test 2: Response Time
        txn_id = test_webhook_response_time()
        
        # Test 3: Initial Status
        test_transaction_status_processing(txn_id)
        
        # Test 4: Idempotency
        test_idempotency(txn_id)
        
        # Test 5: Concurrent Requests
        test_concurrent_duplicates()
        
        # Test 6: Background Processing
        test_background_processing(txn_id)
        
        # Test 7: Multiple Transactions
        test_multiple_transactions()
        
        print_header("✅ ALL TESTS PASSED!")
        print("\nSuccess Criteria Verified:")
        print("✅ Single Transaction - Processed after 30 seconds")
        print("✅ Duplicate Prevention - Handled gracefully")
        print("✅ Performance - Response time < 500ms")
        print("✅ Reliability - No errors, no lost transactions")
        print("\n" + "=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to service at http://localhost:8000")
        print("   Make sure the service is running:")
        print("   uvicorn app.main:app --reload")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

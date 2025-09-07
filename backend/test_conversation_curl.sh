#!/bin/bash

# Test conversation context persistence using curl
# This script sends two messages and checks if context is maintained

API_URL="http://localhost:8000"
TENANT_ID="tenant_Tgyrz826g6McXjlQX173RA"
SESSION_ID="test_session_$(date +%s)"

echo "=========================================="
echo "TESTING CONVERSATION CONTEXT WITH CURL"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# First message - establish context
echo "[1] Sending first message to establish context..."
curl -X POST "$API_URL/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "message": "My name is Alice and I love ice cream.",
    "session_id": "'$SESSION_ID'",
    "use_redis_conversations": true,
    "use_rag": false
  }' \
  --no-buffer 2>/dev/null | grep -o '"content":"[^"]*"' | head -5

echo ""
echo "[2] Waiting 2 seconds..."
sleep 2

# Second message - test context recall
echo ""
echo "[3] Sending second message to test context recall..."
echo "    Question: 'What is my name and what do I love?'"
echo ""
echo "Response:"
curl -X POST "$API_URL/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "message": "What is my name and what do I love?",
    "session_id": "'$SESSION_ID'",
    "use_redis_conversations": true,
    "use_rag": false
  }' \
  --no-buffer 2>/dev/null | grep -o '"content":"[^"]*"' | sed 's/"content":"//g' | sed 's/"//g' | tr -d '\n'

echo ""
echo ""
echo "=========================================="
echo "TEST COMPLETE"
echo "=========================================="
echo ""
echo "✅ If the response mentions 'Alice' and 'ice cream', context is working!"
echo "❌ If the response doesn't know these details, context is NOT working."
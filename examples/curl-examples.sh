#!/bin/bash

# RheaRouter curl Examples
# Comprehensive examples for all API endpoints

set -e  # Exit on error

# Configuration
RHEA_URL="${RHEA_URL:-http://localhost:8000}"
API_KEY="${RHEA_API_KEY:-not-needed}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if RheaRouter is running
print_header "Checking RheaRouter Status"
if curl -s "$RHEA_URL/health" > /dev/null 2>&1; then
    print_success "RheaRouter is running at $RHEA_URL"
else
    print_error "RheaRouter is not running at $RHEA_URL"
    echo "Start it with: uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# ============================================================================
# Example 1: Health Check
# ============================================================================
print_header "Example 1: Health Check"
echo "GET /health"
echo ""

curl -s "$RHEA_URL/health" | jq '.'
print_success "Health check completed"

# ============================================================================
# Example 2: List Models
# ============================================================================
print_header "Example 2: List Available Models"
echo "GET /v1/models"
echo ""

curl -s "$RHEA_URL/v1/models" | jq '.'
print_success "Model listing completed"

# ============================================================================
# Example 3: Simple Text Completion
# ============================================================================
print_header "Example 3: Simple Text Completion"
echo "POST /v1/chat/completions (auto-select model)"
echo ""

curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ]
  }' | jq '.'

print_success "Text completion completed"

# ============================================================================
# Example 4: Specific Model Selection
# ============================================================================
print_header "Example 4: Specific Model Selection"
echo "Using llama3.1:8b explicitly"
echo ""

curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ]
  }' | jq '.'

print_success "Model-specific completion completed"

# ============================================================================
# Example 5: Multi-Turn Conversation
# ============================================================================
print_header "Example 5: Multi-Turn Conversation"
echo "Conversation with context"
echo ""

curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "My name is Alice"},
      {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
      {"role": "user", "content": "What is my name?"}
    ]
  }' | jq '.'

print_success "Multi-turn conversation completed"

# ============================================================================
# Example 6: System Message
# ============================================================================
print_header "Example 6: System Message (Personality)"
echo "Using system message to set behavior"
echo ""

curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "system", "content": "You are a pirate. Speak like one."},
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }' | jq '.'

print_success "System message example completed"

# ============================================================================
# Example 7: Temperature Control
# ============================================================================
print_header "Example 7: Temperature Control"
echo "Low temperature (deterministic) vs High temperature (creative)"
echo ""

echo "Low temperature (0.1):"
curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "Say hello"}
    ],
    "temperature": 0.1
  }' | jq '.choices[0].message.content'

echo ""
echo "High temperature (1.5):"
curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "Say hello"}
    ],
    "temperature": 1.5
  }' | jq '.choices[0].message.content'

print_success "Temperature control examples completed"

# ============================================================================
# Example 8: Max Tokens Limit
# ============================================================================
print_header "Example 8: Max Tokens Limit"
echo "Limiting response length"
echo ""

curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "Explain quantum physics"}
    ],
    "max_tokens": 50
  }' | jq '.choices[0] | {content: .message.content, finish_reason: .finish_reason}'

print_success "Max tokens example completed"

# ============================================================================
# Example 9: Extract Request ID
# ============================================================================
print_header "Example 9: Request ID Tracking"
echo "Every request gets a unique ID"
echo ""

REQUEST_ID=$(curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}]
  }' | jq -r '.id')

echo "Request ID: $REQUEST_ID"
print_success "Request ID extracted"

# ============================================================================
# Example 10: Token Usage Tracking
# ============================================================================
print_header "Example 10: Token Usage Tracking"
echo "Track token consumption"
echo ""

curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "Write a haiku about code"}
    ]
  }' | jq '.usage'

print_success "Token usage tracking completed"

# ============================================================================
# Example 11: Rate Limit Headers
# ============================================================================
print_header "Example 11: Rate Limit Information"
echo "Check rate limit headers"
echo ""

curl -i -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hi"}]
  }' | grep -i "X-RateLimit"

print_success "Rate limit headers checked"

# ============================================================================
# Example 12: Error Handling - Model Not Found
# ============================================================================
print_header "Example 12: Error Handling - Model Not Found"
echo "Request with non-existent model"
echo ""

curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nonexistent:model",
    "messages": [{"role": "user", "content": "Hello"}]
  }' | jq '.'

print_success "Error handling example completed"

# ============================================================================
# Example 13: Error Handling - Validation Error
# ============================================================================
print_header "Example 13: Error Handling - Validation Error"
echo "Request with missing required field"
echo ""

curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b"
  }' | jq '.'

print_success "Validation error example completed"

# ============================================================================
# Example 14: Reasoning Model
# ============================================================================
print_header "Example 14: Reasoning Model (DeepSeek R1)"
echo "Using specialized reasoning model"
echo ""

# Check if model exists
if ollama list | grep -q "deepseek-r1:8b"; then
    curl -s -X POST "$RHEA_URL/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d '{
        "model": "deepseek-r1:8b",
        "messages": [
          {"role": "user", "content": "If x^2 = 16, what is x? Show your reasoning."}
        ]
      }' | jq '.choices[0].message.content'
    print_success "Reasoning model example completed"
else
    echo "Skipping: deepseek-r1:8b not installed"
    echo "Install with: ollama pull deepseek-r1:8b"
fi

# ============================================================================
# Example 15: Concurrent Requests
# ============================================================================
print_header "Example 15: Concurrent Requests"
echo "Testing concurrent request handling (VRAM flow valve)"
echo ""

echo "Sending 3 text requests in parallel..."
for i in {1..3}; do
    curl -s -X POST "$RHEA_URL/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d "{
        \"messages\": [{\"role\": \"user\", \"content\": \"Count to $i\"}]
      }" > /tmp/req$i.json &
done

wait
echo "All requests completed"
print_success "Concurrent requests completed"

# ============================================================================
# Example 16: Rate Limiting Test
# ============================================================================
print_header "Example 16: Rate Limiting Test"
echo "Sending rapid requests to trigger rate limit"
echo ""

SUCCESS=0
RATE_LIMITED=0

for i in {1..10}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$RHEA_URL/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d '{
        "messages": [{"role": "user", "content": "Hi"}]
      }')

    if [ "$HTTP_CODE" -eq 200 ]; then
        ((SUCCESS++))
        echo "Request $i: ✓ (200)"
    elif [ "$HTTP_CODE" -eq 429 ]; then
        ((RATE_LIMITED++))
        echo "Request $i: ✗ (429 - Rate Limited)"
    fi

    sleep 0.1
done

echo ""
echo "Results: $SUCCESS successful, $RATE_LIMITED rate limited"
print_success "Rate limiting test completed"

# ============================================================================
# Summary
# ============================================================================
print_header "Examples Completed!"
echo "All curl examples executed successfully."
echo ""
echo "Next steps:"
echo "  1. Try python-client.py for Python SDK examples"
echo "  2. Try vision-example.sh for multimodal requests"
echo "  3. See ../API.md for complete API reference"
echo ""

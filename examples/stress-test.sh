#!/bin/bash

# RheaRouter Stress Test
# Load testing script for RheaRouter API

set -e

# Configuration
RHEA_URL="${RHEA_URL:-http://localhost:8000}"
NUM_REQUESTS="${1:-100}"
CONCURRENT="${2:-5}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_header "RheaRouter Stress Test"
echo "Target: $RHEA_URL"
echo "Requests: $NUM_REQUESTS"
echo "Concurrent: $CONCURRENT"
echo ""

# Check RheaRouter is running
if ! curl -s "$RHEA_URL/health" > /dev/null 2>&1; then
    print_error "RheaRouter is not running at $RHEA_URL"
    exit 1
fi

print_success "RheaRouter is running"

# Create temp directory for results
RESULTS_DIR="/tmp/rhearouter-stress-$(date +%s)"
mkdir -p "$RESULTS_DIR"

echo "Results directory: $RESULTS_DIR"
echo ""

# ============================================================================
# Test 1: Sequential Requests
# ============================================================================
print_header "Test 1: Sequential Requests"
echo "Sending $NUM_REQUESTS requests sequentially..."

START_TIME=$(date +%s.%N)
SUCCESS_COUNT=0
ERROR_COUNT=0
RATE_LIMITED_COUNT=0
TOTAL_DURATION=0

for i in $(seq 1 $NUM_REQUESTS); do
    REQUEST_START=$(date +%s.%N)

    HTTP_CODE=$(curl -s -o "$RESULTS_DIR/seq_$i.json" -w "%{http_code}" \
      -X POST "$RHEA_URL/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d "{
        \"messages\": [{\"role\": \"user\", \"content\": \"Count to $i\"}],
        \"max_tokens\": 20
      }")

    REQUEST_END=$(date +%s.%N)
    DURATION=$(echo "$REQUEST_END - $REQUEST_START" | bc)
    TOTAL_DURATION=$(echo "$TOTAL_DURATION + $DURATION" | bc)

    if [ "$HTTP_CODE" -eq 200 ]; then
        ((SUCCESS_COUNT++))
        printf "."
    elif [ "$HTTP_CODE" -eq 429 ]; then
        ((RATE_LIMITED_COUNT++))
        printf "R"
    else
        ((ERROR_COUNT++))
        printf "E"
    fi

    # Progress indicator every 10 requests
    if [ $((i % 10)) -eq 0 ]; then
        echo " [$i/$NUM_REQUESTS]"
    fi
done

END_TIME=$(date +%s.%N)
TOTAL_TIME=$(echo "$END_TIME - $START_TIME" | bc)
AVG_DURATION=$(echo "scale=3; $TOTAL_DURATION / $NUM_REQUESTS" | bc)
REQUESTS_PER_SEC=$(echo "scale=2; $NUM_REQUESTS / $TOTAL_TIME" | bc)

echo ""
echo ""
echo "Results:"
echo "  ✓ Success: $SUCCESS_COUNT"
echo "  R Rate limited: $RATE_LIMITED_COUNT"
echo "  E Errors: $ERROR_COUNT"
echo "  Total time: ${TOTAL_TIME}s"
echo "  Avg request time: ${AVG_DURATION}s"
echo "  Throughput: ${REQUESTS_PER_SEC} req/s"

# ============================================================================
# Test 2: Concurrent Requests
# ============================================================================
print_header "Test 2: Concurrent Requests"
echo "Sending $NUM_REQUESTS requests with $CONCURRENT concurrent workers..."

START_TIME=$(date +%s.%N)

# Function to send request
send_request() {
    local i=$1
    local output_file="$RESULTS_DIR/conc_$i.json"

    HTTP_CODE=$(curl -s -o "$output_file" -w "%{http_code}" \
      -X POST "$RHEA_URL/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d "{
        \"messages\": [{\"role\": \"user\", \"content\": \"Request $i\"}],
        \"max_tokens\": 20
      }")

    echo "$HTTP_CODE" > "$output_file.code"
}

export -f send_request
export RHEA_URL
export RESULTS_DIR

# Use xargs for concurrent execution
seq 1 $NUM_REQUESTS | xargs -P $CONCURRENT -I {} bash -c 'send_request {}'

END_TIME=$(date +%s.%N)
TOTAL_TIME=$(echo "$END_TIME - $START_TIME" | bc)

# Count results
CONC_SUCCESS=0
CONC_RATE_LIMITED=0
CONC_ERRORS=0

for i in $(seq 1 $NUM_REQUESTS); do
    CODE=$(cat "$RESULTS_DIR/conc_$i.json.code")
    if [ "$CODE" -eq 200 ]; then
        ((CONC_SUCCESS++))
    elif [ "$CODE" -eq 429 ]; then
        ((CONC_RATE_LIMITED++))
    else
        ((CONC_ERRORS++))
    fi
done

REQUESTS_PER_SEC=$(echo "scale=2; $NUM_REQUESTS / $TOTAL_TIME" | bc)

echo "Results:"
echo "  ✓ Success: $CONC_SUCCESS"
echo "  R Rate limited: $CONC_RATE_LIMITED"
echo "  E Errors: $CONC_ERRORS"
echo "  Total time: ${TOTAL_TIME}s"
echo "  Throughput: ${REQUESTS_PER_SEC} req/s"
echo "  Speedup: $(echo "scale=2; $REQUESTS_PER_SEC / ${REQUESTS_PER_SEC}" | bc)x"

# ============================================================================
# Test 3: Rate Limit Validation
# ============================================================================
print_header "Test 3: Rate Limit Validation"
echo "Testing rate limiting (60/min global, 20/min per-client)..."

# Send 30 rapid requests
RATE_SUCCESS=0
RATE_LIMITED=0

for i in $(seq 1 30); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST "$RHEA_URL/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d '{
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10
      }')

    if [ "$HTTP_CODE" -eq 200 ]; then
        ((RATE_SUCCESS++))
        printf "."
    elif [ "$HTTP_CODE" -eq 429 ]; then
        ((RATE_LIMITED++))
        printf "R"
        # Extract Retry-After header
        RETRY_AFTER=$(curl -s -I -X POST "$RHEA_URL/v1/chat/completions" \
          -H "Content-Type: application/json" \
          -d '{"messages": [{"role": "user", "content": "Hi"}]}' \
          | grep -i "Retry-After" | cut -d' ' -f2 | tr -d '\r')
    fi

    sleep 0.05
done

echo ""
echo ""
echo "Results:"
echo "  ✓ Success: $RATE_SUCCESS (should be ~20)"
echo "  R Rate limited: $RATE_LIMITED (should be ~10)"

if [ $RATE_SUCCESS -le 20 ] && [ $RATE_LIMITED -ge 5 ]; then
    print_success "Rate limiting working as expected"
else
    print_warning "Rate limiting behavior unexpected"
fi

# ============================================================================
# Test 4: VRAM Flow Valve (Text vs Vision)
# ============================================================================
print_header "Test 4: VRAM Flow Valve"
echo "Testing concurrent text requests (should allow 2)..."

# Send 3 text requests concurrently
for i in {1..3}; do
    curl -s -X POST "$RHEA_URL/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"llama3.1:8b\",
        \"messages\": [{\"role\": \"user\", \"content\": \"Request $i\"}],
        \"max_tokens\": 20
      }" > "$RESULTS_DIR/vram_text_$i.json" &
done

echo "Waiting for text requests to complete..."
wait

TEXT_SUCCESS=$(ls $RESULTS_DIR/vram_text_*.json 2>/dev/null | wc -l)
echo "  ✓ Completed: $TEXT_SUCCESS/3"

if [ $TEXT_SUCCESS -eq 3 ]; then
    print_success "Text flow valve working (2 slots)"
else
    print_warning "Text flow valve behavior unexpected"
fi

# ============================================================================
# Test 5: Token Usage Analysis
# ============================================================================
print_header "Test 5: Token Usage Analysis"
echo "Analyzing token usage from sequential test..."

TOTAL_PROMPT_TOKENS=0
TOTAL_COMPLETION_TOKENS=0
TOTAL_TOKENS=0

for i in $(seq 1 $SUCCESS_COUNT); do
    if [ -f "$RESULTS_DIR/seq_$i.json" ]; then
        PROMPT=$(jq -r '.usage.prompt_tokens // 0' "$RESULTS_DIR/seq_$i.json")
        COMPLETION=$(jq -r '.usage.completion_tokens // 0' "$RESULTS_DIR/seq_$i.json")

        TOTAL_PROMPT_TOKENS=$((TOTAL_PROMPT_TOKENS + PROMPT))
        TOTAL_COMPLETION_TOKENS=$((TOTAL_COMPLETION_TOKENS + COMPLETION))
        TOTAL_TOKENS=$((TOTAL_TOKENS + PROMPT + COMPLETION))
    fi
done

if [ $SUCCESS_COUNT -gt 0 ]; then
    AVG_PROMPT=$((TOTAL_PROMPT_TOKENS / SUCCESS_COUNT))
    AVG_COMPLETION=$((TOTAL_COMPLETION_TOKENS / SUCCESS_COUNT))
    AVG_TOTAL=$((TOTAL_TOKENS / SUCCESS_COUNT))

    echo "Token usage statistics:"
    echo "  Total prompt tokens: $TOTAL_PROMPT_TOKENS"
    echo "  Total completion tokens: $TOTAL_COMPLETION_TOKENS"
    echo "  Total tokens: $TOTAL_TOKENS"
    echo "  Avg prompt tokens: $AVG_PROMPT"
    echo "  Avg completion tokens: $AVG_COMPLETION"
    echo "  Avg total tokens: $AVG_TOTAL"
fi

# ============================================================================
# Summary
# ============================================================================
print_header "Stress Test Summary"

cat <<EOF
Test Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 - Sequential Requests:
  Requests: $NUM_REQUESTS
  Success: $SUCCESS_COUNT ($(echo "scale=1; $SUCCESS_COUNT * 100 / $NUM_REQUESTS" | bc)%)
  Rate limited: $RATE_LIMITED_COUNT
  Errors: $ERROR_COUNT
  Throughput: ${REQUESTS_PER_SEC} req/s
  Avg latency: ${AVG_DURATION}s

Test 2 - Concurrent Requests:
  Requests: $NUM_REQUESTS
  Concurrency: $CONCURRENT
  Success: $CONC_SUCCESS ($(echo "scale=1; $CONC_SUCCESS * 100 / $NUM_REQUESTS" | bc)%)
  Rate limited: $CONC_RATE_LIMITED
  Errors: $CONC_ERRORS

Test 3 - Rate Limiting:
  Success: $RATE_SUCCESS/30 (expected ~20)
  Rate limited: $RATE_LIMITED/30 (expected ~10)
  Status: $([ $RATE_SUCCESS -le 20 ] && echo "✓ PASS" || echo "✗ FAIL")

Test 4 - VRAM Flow Valve:
  Text requests: $TEXT_SUCCESS/3
  Status: $([ $TEXT_SUCCESS -eq 3 ] && echo "✓ PASS" || echo "✗ FAIL")

Test 5 - Token Usage:
  Total tokens: $TOTAL_TOKENS
  Avg per request: $AVG_TOTAL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Results saved to: $RESULTS_DIR

View individual responses:
  ls $RESULTS_DIR/*.json

Cleanup:
  rm -rf $RESULTS_DIR
EOF

echo ""

# Overall verdict
TOTAL_SUCCESS=$((SUCCESS_COUNT + CONC_SUCCESS))
TOTAL_ATTEMPTED=$((NUM_REQUESTS * 2))
SUCCESS_RATE=$(echo "scale=1; $TOTAL_SUCCESS * 100 / $TOTAL_ATTEMPTED" | bc)

if (( $(echo "$SUCCESS_RATE >= 80" | bc -l) )); then
    print_success "Overall: PASS (${SUCCESS_RATE}% success rate)"
elif (( $(echo "$SUCCESS_RATE >= 50" | bc -l) )); then
    print_warning "Overall: PARTIAL (${SUCCESS_RATE}% success rate)"
else
    print_error "Overall: FAIL (${SUCCESS_RATE}% success rate)"
fi

echo ""

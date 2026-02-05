#!/bin/bash

# RheaRouter Vision Example
# Demonstrates multimodal (image + text) requests

set -e

# Configuration
RHEA_URL="${RHEA_URL:-http://localhost:8000}"
VISION_MODEL="${VISION_MODEL:-minicpm-v:8b}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

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

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <image-path> [question]"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/image.jpg"
    echo "  $0 /path/to/image.jpg \"What do you see in this image?\""
    echo "  $0 /path/to/screenshot.png \"What text is visible?\""
    echo ""
    exit 1
fi

IMAGE_PATH="$1"
QUESTION="${2:-What do you see in this image?}"

# Validate image exists
if [ ! -f "$IMAGE_PATH" ]; then
    print_error "Image not found: $IMAGE_PATH"
    exit 1
fi

# Check file type
FILE_TYPE=$(file -b --mime-type "$IMAGE_PATH")
if [[ ! "$FILE_TYPE" =~ ^image/ ]]; then
    print_error "Not an image file: $IMAGE_PATH (detected: $FILE_TYPE)"
    exit 1
fi

print_header "RheaRouter Vision Example"
echo "Image: $IMAGE_PATH"
echo "Question: $QUESTION"
echo "Model: $VISION_MODEL"
echo ""

# Check RheaRouter is running
if ! curl -s "$RHEA_URL/health" > /dev/null 2>&1; then
    print_error "RheaRouter is not running at $RHEA_URL"
    echo "Start it with: uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# Check model is available
if ! ollama list | grep -q "$VISION_MODEL"; then
    print_error "Vision model not found: $VISION_MODEL"
    echo "Install it with: ollama pull $VISION_MODEL"
    exit 1
fi

print_success "Prerequisites checked"

# Encode image to base64
print_header "Encoding Image"
echo "Encoding $IMAGE_PATH to base64..."

# Detect image format
case "$FILE_TYPE" in
    image/jpeg)
        MIME_TYPE="image/jpeg"
        ;;
    image/png)
        MIME_TYPE="image/png"
        ;;
    image/gif)
        MIME_TYPE="image/gif"
        ;;
    image/webp)
        MIME_TYPE="image/webp"
        ;;
    *)
        print_error "Unsupported image format: $FILE_TYPE"
        echo "Supported: JPEG, PNG, GIF, WebP"
        exit 1
        ;;
esac

# Encode image
BASE64_IMAGE=$(base64 -w 0 "$IMAGE_PATH")
IMAGE_SIZE=$(echo -n "$BASE64_IMAGE" | wc -c)
IMAGE_SIZE_MB=$(echo "scale=2; $IMAGE_SIZE / 1024 / 1024" | bc)

echo "  Format: $MIME_TYPE"
echo "  Encoded size: ${IMAGE_SIZE_MB}MB"

# Check size limit (10MB)
if (( $(echo "$IMAGE_SIZE_MB > 10" | bc -l) )); then
    print_error "Image too large: ${IMAGE_SIZE_MB}MB (max 10MB)"
    echo "Compress the image and try again"
    exit 1
fi

print_success "Image encoded successfully"

# Build data URL
DATA_URL="data:${MIME_TYPE};base64,${BASE64_IMAGE}"

# Send vision request
print_header "Sending Vision Request"
echo "Analyzing image with $VISION_MODEL..."
echo ""

# Create request payload
REQUEST_PAYLOAD=$(cat <<EOF
{
  "model": "$VISION_MODEL",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "$QUESTION"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "$DATA_URL"
          }
        }
      ]
    }
  ],
  "temperature": 0.7,
  "max_tokens": 500
}
EOF
)

# Send request and save response
RESPONSE=$(curl -s -X POST "$RHEA_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_PAYLOAD")

# Check for errors
if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    print_error "Request failed"
    echo "$RESPONSE" | jq '.error'
    exit 1
fi

# Extract response
CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content')
MODEL=$(echo "$RESPONSE" | jq -r '.model')
TOKENS=$(echo "$RESPONSE" | jq -r '.usage.total_tokens')
REQUEST_ID=$(echo "$RESPONSE" | jq -r '.id')

# Display results
print_header "Vision Response"
echo "Model: $MODEL"
echo "Tokens: $TOKENS"
echo "Request ID: $REQUEST_ID"
echo ""
echo "Question: $QUESTION"
echo ""
echo "Answer:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$CONTENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

print_success "Vision request completed"

# Save full response
OUTPUT_FILE="/tmp/vision-response-$(date +%s).json"
echo "$RESPONSE" | jq '.' > "$OUTPUT_FILE"
echo "Full response saved to: $OUTPUT_FILE"

# ============================================================================
# Additional Examples
# ============================================================================
print_header "Try These Examples"

cat <<EOF
# OCR (text extraction)
$0 $IMAGE_PATH "Extract all text from this image"

# Detailed description
$0 $IMAGE_PATH "Describe this image in detail, including colors, objects, and layout"

# Specific question
$0 $IMAGE_PATH "How many people are in this image?"

# Technical analysis
$0 $IMAGE_PATH "What code is shown in this screenshot? Explain what it does."

# Comparison (requires two images)
# First, analyze image 1, then image 2, then compare manually
EOF

echo ""

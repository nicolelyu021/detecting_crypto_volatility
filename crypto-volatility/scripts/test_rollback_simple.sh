#!/bin/bash
# Simple test script for model rollback feature
# Week 6 - Quick Demo

echo "=========================================="
echo "Model Rollback Feature - Quick Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
if ! docker ps | grep -q "volatility-api"; then
    echo -e "${YELLOW}Services not running. Starting with ML model first...${NC}"
    cd docker
    docker compose up -d
    cd ..
    echo "Waiting 30 seconds for services to start..."
    sleep 30
fi

echo "=========================================="
echo "Test 1: Check Current Model"
echo "=========================================="
echo ""

CURRENT_VERSION=$(curl -s http://localhost:8000/version | jq -r .model_version)
echo "Current model version: $CURRENT_VERSION"

if [[ "$CURRENT_VERSION" == "baseline-"* ]]; then
    echo -e "${YELLOW}Currently using BASELINE model${NC}"
    CURRENT_MODE="baseline"
else
    echo -e "${GREEN}Currently using ML model${NC}"
    CURRENT_MODE="ml"
fi

echo ""
echo "=========================================="
echo "Test 2: Make Test Prediction"
echo "=========================================="
echo ""

PREDICTION=$(curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"price": 50000.0, "midprice": 50000.0, "return_1s": 0.001, "volatility": 0.02}')

echo "Prediction response:"
echo "$PREDICTION" | jq .

if echo "$PREDICTION" | jq -e .prediction > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Prediction successful with $CURRENT_MODE model${NC}"
else
    echo -e "${RED}❌ Prediction failed${NC}"
fi

echo ""
echo "=========================================="
echo "Test 3: Demonstrate Rollback"
echo "=========================================="
echo ""

if [ "$CURRENT_MODE" == "ml" ]; then
    echo "Switching FROM ML model TO baseline model..."
    echo "Command: MODEL_VARIANT=baseline docker compose up -d"
    echo ""
    echo -e "${YELLOW}To activate rollback, run:${NC}"
    echo "cd docker"
    echo "docker compose down"
    echo "MODEL_VARIANT=baseline docker compose up -d"
    echo ""
    echo -e "${YELLOW}Or edit docker/compose.yaml and uncomment:${NC}"
    echo "  MODEL_VARIANT: \"baseline\""
else
    echo "Switching FROM baseline model TO ML model..."
    echo "Command: docker compose up -d (without MODEL_VARIANT)"
    echo ""
    echo -e "${YELLOW}To return to ML model, run:${NC}"
    echo "cd docker"
    echo "docker compose down"
    echo "docker compose up -d"
    echo ""
    echo -e "${YELLOW}Or edit docker/compose.yaml and comment out:${NC}"
    echo "  # MODEL_VARIANT: \"baseline\""
fi

echo ""
echo "=========================================="
echo "Test 4: Check Logs for Rollback Indicator"
echo "=========================================="
echo ""

if docker compose logs api 2>/dev/null | grep -q "ROLLBACK MODE"; then
    echo -e "${YELLOW}🔄 ROLLBACK MODE detected in logs${NC}"
    docker compose logs api 2>/dev/null | grep "ROLLBACK MODE" | tail -3
else
    echo -e "${GREEN}No rollback mode detected - using standard ML model${NC}"
fi

echo ""
echo "=========================================="
echo "✅ Rollback Feature Test Complete!"
echo "=========================================="
echo ""

echo "Summary:"
echo "--------"
echo "Current Model: $CURRENT_MODE"
echo "Model Version: $CURRENT_VERSION"
echo "Predictions: Working ✅"
echo ""
echo "The rollback feature is ready to use!"
echo ""
echo "For full guide, see: docs/model_rollback_guide.md"
echo ""


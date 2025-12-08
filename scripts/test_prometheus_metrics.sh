#!/bin/bash
# Test script to verify Prometheus metrics are working
# Week 6 - Prometheus Metrics Setup

echo "=================================================="
echo "Testing Prometheus Metrics Setup"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "1. Checking if services are running..."
echo ""

if ! docker ps | grep -q "volatility-api"; then
    echo -e "${RED}❌ API service is not running${NC}"
    echo "   Run: cd docker && docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ API service is running${NC}"

if ! docker ps | grep -q "prometheus"; then
    echo -e "${RED}❌ Prometheus is not running${NC}"
    echo "   Run: cd docker && docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ Prometheus is running${NC}"

if ! docker ps | grep -q "grafana"; then
    echo -e "${YELLOW}⚠️  Grafana is not running (optional for this test)${NC}"
else
    echo -e "${GREEN}✅ Grafana is running${NC}"
fi

if ! docker ps | grep -q "volatility-prediction-consumer"; then
    echo -e "${YELLOW}⚠️  Consumer is not running (will skip consumer metrics)${NC}"
    CONSUMER_RUNNING=false
else
    echo -e "${GREEN}✅ Consumer is running${NC}"
    CONSUMER_RUNNING=true
fi

echo ""
echo "=================================================="
echo "2. Testing API Metrics Endpoint"
echo "=================================================="
echo ""

# Test API metrics endpoint
echo "Fetching metrics from http://localhost:8000/metrics..."
API_METRICS=$(curl -s http://localhost:8000/metrics 2>/dev/null)

if [ -z "$API_METRICS" ]; then
    echo -e "${RED}❌ Could not fetch API metrics${NC}"
    exit 1
fi

echo -e "${GREEN}✅ API metrics endpoint is accessible${NC}"
echo ""

# Check for specific metrics
echo "Checking for expected metrics..."

if echo "$API_METRICS" | grep -q "volatility_api_requests_total"; then
    echo -e "${GREEN}✅ Found: volatility_api_requests_total${NC}"
else
    echo -e "${RED}❌ Missing: volatility_api_requests_total${NC}"
fi

if echo "$API_METRICS" | grep -q "volatility_api_errors_total"; then
    echo -e "${GREEN}✅ Found: volatility_api_errors_total${NC}"
else
    echo -e "${RED}❌ Missing: volatility_api_errors_total${NC}"
fi

if echo "$API_METRICS" | grep -q "volatility_prediction_latency_seconds"; then
    echo -e "${GREEN}✅ Found: volatility_prediction_latency_seconds${NC}"
else
    echo -e "${RED}❌ Missing: volatility_prediction_latency_seconds${NC}"
fi

if echo "$API_METRICS" | grep -q "volatility_api_health_status"; then
    echo -e "${GREEN}✅ Found: volatility_api_health_status${NC}"
else
    echo -e "${RED}❌ Missing: volatility_api_health_status${NC}"
fi

echo ""
echo "=================================================="
echo "3. Testing Health Endpoint"
echo "=================================================="
echo ""

HEALTH=$(curl -s http://localhost:8000/health)
echo "Health status: $HEALTH"

if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  API health check returned: $HEALTH${NC}"
fi

echo ""
echo "=================================================="
echo "4. Making Test Prediction"
echo "=================================================="
echo ""

echo "Sending test prediction request..."
PREDICT_RESPONSE=$(curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "price": 50000.0,
    "midprice": 50000.0,
    "return_1s": 0.001,
    "return_5s": 0.002,
    "return_30s": 0.005,
    "return_60s": 0.01,
    "volatility": 0.02,
    "trade_intensity": 10.0,
    "spread_abs": 1.0,
    "spread_rel": 0.0001,
    "order_book_imbalance": 0.05
  }')

if echo "$PREDICT_RESPONSE" | grep -q "prediction"; then
    echo -e "${GREEN}✅ Prediction successful${NC}"
    echo "Response: $PREDICT_RESPONSE"
else
    echo -e "${RED}❌ Prediction failed${NC}"
    echo "Response: $PREDICT_RESPONSE"
fi

echo ""
echo "=================================================="
echo "5. Verifying Metrics Updated"
echo "=================================================="
echo ""

# Wait a moment for metrics to update
sleep 2

# Check if prediction counter increased
NEW_METRICS=$(curl -s http://localhost:8000/metrics 2>/dev/null)

if echo "$NEW_METRICS" | grep -q "volatility_predictions_total"; then
    PREDICTION_COUNT=$(echo "$NEW_METRICS" | grep "volatility_predictions_total" | grep -v "#" | head -1)
    echo -e "${GREEN}✅ Prediction counter updated${NC}"
    echo "   $PREDICTION_COUNT"
else
    echo -e "${RED}❌ Prediction counter not found${NC}"
fi

if echo "$NEW_METRICS" | grep -q "volatility_prediction_latency_seconds_count"; then
    LATENCY_COUNT=$(echo "$NEW_METRICS" | grep "volatility_prediction_latency_seconds_count" | head -1)
    echo -e "${GREEN}✅ Latency histogram updated${NC}"
    echo "   $LATENCY_COUNT"
else
    echo -e "${YELLOW}⚠️  Latency histogram not updated yet${NC}"
fi

echo ""

# Test consumer metrics if consumer is running
if [ "$CONSUMER_RUNNING" = true ]; then
    echo "=================================================="
    echo "6. Testing Consumer Metrics"
    echo "=================================================="
    echo ""
    
    echo "Fetching metrics from http://localhost:8001/metrics..."
    CONSUMER_METRICS=$(curl -s http://localhost:8001/metrics 2>/dev/null)
    
    if [ -z "$CONSUMER_METRICS" ]; then
        echo -e "${YELLOW}⚠️  Could not fetch consumer metrics (port may not be exposed)${NC}"
    else
        echo -e "${GREEN}✅ Consumer metrics endpoint is accessible${NC}"
        
        if echo "$CONSUMER_METRICS" | grep -q "volatility_consumer_messages_processed_total"; then
            echo -e "${GREEN}✅ Found: volatility_consumer_messages_processed_total${NC}"
        fi
        
        if echo "$CONSUMER_METRICS" | grep -q "volatility_consumer_lag_seconds"; then
            echo -e "${GREEN}✅ Found: volatility_consumer_lag_seconds${NC}"
        fi
        
        if echo "$CONSUMER_METRICS" | grep -q "volatility_consumer_processing_rate"; then
            echo -e "${GREEN}✅ Found: volatility_consumer_processing_rate${NC}"
        fi
    fi
    echo ""
fi

echo "=================================================="
echo "7. Checking Prometheus Targets"
echo "=================================================="
echo ""

echo "Checking Prometheus targets status..."
TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null)

if echo "$TARGETS" | grep -q '"health":"up"'; then
    echo -e "${GREEN}✅ Prometheus is successfully scraping targets${NC}"
    
    if echo "$TARGETS" | grep -q 'volatility-api'; then
        echo -e "${GREEN}   ✅ API target is UP${NC}"
    else
        echo -e "${YELLOW}   ⚠️  API target not found in Prometheus${NC}"
    fi
    
    if echo "$TARGETS" | grep -q 'volatility-consumer'; then
        echo -e "${GREEN}   ✅ Consumer target is UP${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Consumer target not found in Prometheus${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Some Prometheus targets may be down${NC}"
    echo "   Check: http://localhost:9090/targets"
fi

echo ""
echo "=================================================="
echo "✅ Prometheus Metrics Testing Complete!"
echo "=================================================="
echo ""
echo "Next Steps:"
echo "1. Open Prometheus UI: http://localhost:9090"
echo "2. Try queries like:"
echo "   - rate(volatility_api_requests_total[1m])"
echo "   - histogram_quantile(0.95, volatility_prediction_latency_seconds_bucket)"
echo "3. Open Grafana: http://localhost:3000 (admin/admin)"
echo "4. Create dashboards using these metrics"
echo ""
echo "For more details, see: docs/prometheus_metrics_guide.md"
echo ""


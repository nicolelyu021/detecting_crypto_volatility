# Milestone 1 Summary – Detecting Crypto Volatility in Real Time

---

## 🎯 Objective
Build the foundational **real-time data ingestion pipeline** that connects live Coinbase ticker data (BTC-USD) to Kafka, validates the data flow, and defines a concise scoping brief for the overall AI volatility-detection project.

---

## ✅ Key Achievements

| Step | What I Did | Outcome |
|------|-------------|----------|
| **1. Project Setup** | Created organized folder structure and `requirements.txt`. | Clear repo layout with `scripts/`, `data/`, `docker/`, and `docs/`. |
| **2. Environment Configuration** | Set up and activated Python virtual environment, installed dependencies (`orjson`, `websockets`, `kafka-python`, etc.). | Verified working environment for development and streaming. |
| **3. Infrastructure Setup** | Configured **Kafka**, **Zookeeper**, and **MLflow** in Docker Compose. | All containers running and accessible (`docker ps` shows all *Up*). |
| **4. Data Ingestion** | Implemented `ws_ingest.py` to stream live **BTC-USD** ticker data from Coinbase WebSocket into Kafka. | Received real JSON messages (price, volume, etc.) in Kafka topic `ticks.raw`. |
| **5. Data Validation** | Built `kafka_consume_check.py` to confirm message flow and count messages. | Output: `messages_seen=20 seconds=3.3` ✅ Data pipeline verified. |
| **6. Data Archiving** | Added file-write logic to store a replay slice at `data/raw/slice.ndjson`. | Local sample of raw data available for testing and replay. |
| **7. Project Documentation** | Authored and exported `docs/scoping_brief.md` → `docs/scoping_brief.pdf`. | Defined project scope, success metrics, risks, and next steps. |
| **8. Containerization** | Created `docker/Dockerfile.ingestor` to containerize the data ingestion script. | Ingestor can now run in Docker, connecting to Kafka via Docker network. Successfully tested with `docker-compose run --rm ingestor`. |

---

## ⚙️ Technical Stack
- **Python**: `asyncio`, `websockets`, `orjson`, `kafka-python`
- **Infrastructure**: Docker + Docker Compose
- **Services**: Kafka, Zookeeper, MLflow
- **Containerization**: Dockerfile.ingestor for containerized data ingestion
- **Data Source**: Coinbase Advanced Trade WebSocket API
- **Format**: JSON (streamed → Kafka topic → local NDJSON slice)

---

## 💡 Challenges & How I Solved Them

| Challenge | Solution |
|------------|-----------|
| Kafka image not found (`bitnami/kafka:3.7`) | Switched to **Confluent Kafka** images (`cp-kafka` + `cp-zookeeper`). |
| Port 5000 conflict for MLflow | Changed MLflow port to **5001** in `compose.yaml`. |
| WebSocket error “No channels provided” | Corrected subscription payload to include `"channels": [{"name": "ticker"}]`. |
| Missing dependency errors | Installed via `pip install -r requirements.txt` after activating virtual environment. |
| Consumer showed `messages_seen=0` | Changed `auto_offset_reset` to `"earliest"` and added `group_id` to consumer config. |
| Docker container couldn't connect to Kafka (`NoBrokersAvailable`) | Updated `ws_ingest.py` to read `KAFKA_SERVERS` from environment variable, set default to `kafka:9092` in Dockerfile, and added ingestor service to `compose.yaml` with proper network configuration. |

---

## 📊 Outcome
Successfully built a **real-time, fault-tolerant data ingestion system** for crypto volatility analysis:
- Streams live BTC-USD tick data from Coinbase.
- Writes to Kafka for downstream processing.
- Archives data locally for reproducibility.
- Containerized ingestion pipeline using Dockerfile.ingestor for production deployment.
- Clearly documented scope and success criteria for future milestones.

---

## 🧠 Reflection
This milestone solidified my understanding of:
- Setting up distributed data pipelines using Docker.
- Handling real-time WebSocket streams and Kafka topics.
- Debugging data infrastructure step-by-step.
- Importance of observability and validation in MLOps pipelines.

---

## 🚀 Next Steps (Milestone 2 Preview)
1. Build **feature extraction** consumer from Kafka stream.  
2. Generate **Evidently AI drift report**.  
3. Define volatility labeling logic and baseline model tracking in MLflow.

# Scoping Brief – Detecting Short-Term Crypto Volatility  

**Use Case:**  
Develop a real-time AI system that predicts **60-second volatility spikes** for **BTC-USD**, enabling traders and risk systems to react faster to market swings. The pipeline uses **Kafka** for data streaming and **MLflow** for tracking, aligning AI performance with measurable business value.

### 1. Prediction Goal and Feasibility  
The model predicts if volatility will exceed a defined threshold within the next 60 seconds.  
**Target horizon:** 60 seconds. **Label rule:** `Label = 1` when future volatility ≥ threshold (to be finalized).  
Success is measured by **PR-AUC ≥ 0.60** and **alert latency < 120 seconds**.  
Traders and risk managers currently monitor volatility manually, which delays response to liquidity changes. A real-time model augments their decision process by providing early alerts. Data comes from the **Coinbase WebSocket feed**—a public, high-frequency, structured source suitable for streaming ML pipelines. All processing is containerized for reproducibility.

### 2. Ethics, Risks, and Assumptions  
The project uses only public data, with no personal or proprietary content. The main ethical risk is over-reactive trading from false alarms. Risks include data outages, market drift, and latency. These are mitigated through continuous drift and quality monitoring with **Evidently**, human-in-the-loop confirmation before automation, and threshold recalibration as distributions shift.  
Operationally, the system assumes stable exchange uptime, consistent data schema, and sufficient hardware resources.

### 3. Business Value  
The system creates value by **reducing reaction time** and **improving alert accuracy**. Automation accelerates detection compared to manual monitoring, while augmentation improves analysts’ confidence by highlighting statistically significant spikes. Even modest gains in precision translate to fewer missed opportunities and lower exposure during high-volatility events. Soft benefits include improved transparency and reproducibility through MLflow logging.

### 4. Roadmap and Success Criteria  
**Milestone 1:** Kafka setup and real-time ingestion completed (≈41 K records).  
**Milestone 2:** Feature engineering and drift analysis, with four windowed features and a 95th-percentile volatility threshold (τ = 0.000028).  
**Milestone 3:** Modeling and evaluation; models tracked in MLflow for accuracy and latency benchmarks.  
The project follows the **Scope → Discover → Deliver → Steward** lifecycle, ensuring every stage links to measurable ROI and responsible operation.
---
**Success Criteria Summary:**  
- Technical: PR-AUC ≥ 0.60 and latency < 2 × window.  
- Operational: Reliable streaming for ≥ 15 minutes without dropouts.  
- Governance: Weekly drift checks and full experiment traceability.  



Reference: 

Rao, A. S. (2025). *Value Scoping* Lecture, CMU Heinz College – *Fundamentals of Operationalizing AI*.
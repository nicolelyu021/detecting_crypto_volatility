# Use of Generative AI – Milestone 1

Prompt (summary): "Guide me step-by-step through Milestone 1 for the Crypto Volatility project, including setting up Docker, Kafka, and a live data ingestion script."
Used in: docker/compose.yaml, scripts/ws_ingest.py, scripts/kafka_consume_check.py  
Verification: I reviewed, understood, and edited all code before running.

Prompt (summary): "Fix Coinbase WebSocket subscription error ('No channels provided') and update subscribe message format."
Used in: scripts/ws_ingest.py  
Verification: I verified messages streamed successfully into Kafka after edit.

Prompt (summary): "Explain why Kafka consumer shows 0 messages and update code accordingly."
Used in: scripts/kafka_consume_check.py  
Verification: I implemented the fix and confirmed message counts worked (`messages_seen=20`).

Prompt (summary): "Generate formatted one-page Scoping Brief defining 60-second volatility goal and success metrics."
Used in: docs/scoping_brief.md  
Verification: I reviewed and edited wording for clarity and accuracy before saving.

Prompt (summary): "Summarize Milestone 1 progress and create professional Markdown log."
Used in: docs/milestone1_log.md  
Verification: I reviewed and finalized the summary before saving.

Prompt (summary): "Create Use of Generative AI appendix in the professor's required format."
Used in: docs/genai_appendix.md  
Verification: I followed the official format exactly per course instruction.

Prompt (summary): "I realized I missed a deliverable from Milestone one. So I just created the Dockerfile.ingestor file and ran it. But I got these errors. First off in the homework requirement pdf, why do we even need this file. and how do we fix the error?"
Used in: docker/Dockerfile.ingestor, docker/compose.yaml, scripts/ws_ingest.py
Verification: I reviewed the Dockerfile, updated it to use environment variables for Kafka connection, modified ws_ingest.py to read KAFKA_SERVERS from environment, added ingestor service to compose.yaml, and successfully tested the containerized ingestion with docker-compose run --rm ingestor.

Prompt (summary): "Can you go through each milestone to see if I achieve 100% of what prof is asking for? My goal is to get 100 on this assignment. Let's start with milestone 1"
Used in: docs/MILESTONE1_REVIEW.md
Verification: I reviewed the assignment PDF requirements for Milestone 1, verified all deliverables exist and function correctly, created comprehensive review document identifying the missing scoping_brief.pdf requirement, and confirmed all other deliverables are complete.

Prompt (summary): "This is what it says in the requirement whether a pdf is needed: Milestone 1 Deliverables: - docker/compose.yaml, docker/Dockerfile.ingestor - scripts/ws_ingest.py and scripts/kafka_consume_check.py - docs/scoping_brief.pdf - config.yaml (if used)"
Used in: docs/scoping_brief.pdf
Verification: I confirmed PDF is required per assignment, converted scoping_brief.md to PDF using pandoc with Unicode character handling (≥ → >=, × → *, ≈ → ~=, τ → tau), and verified PDF file was created successfully (110KB).

Prompt (summary): "I updated the scoping brief to reflect what I learned in class like some business concept. Can you turn that into pdf"
Used in: docs/scoping_brief.pdf
Verification: I converted the updated markdown (with business concepts from Value Scoping lecture) to PDF, handling all Unicode characters, and verified PDF creation (117KB).

Prompt (summary): "I trimmed down the md file now turn it into pdf"
Used in: docs/scoping_brief.pdf
Verification: I converted the trimmed markdown version to PDF, handling Unicode characters, and verified final PDF creation (132KB). The trimmed version maintains business concepts while being more concise.

Prompt (summary): "I have milestone 1 review and milestone 1 checklist. Do I need to keep both?"
Used in: docs/MILESTONE1_CHECKLIST.md (deleted), docs/MILESTONE1_REVIEW.md (kept)
Verification: I compared both documents, identified that MILESTONE1_CHECKLIST.md was outdated (showed PDF as missing when it was completed), and deleted the redundant checklist keeping only the comprehensive review document which is current and accurate.

# Use of Generative AI – Milestone 2

Prompt (summary): "I need to start Milestone 2: Feature Engineering, EDA & Evidently. Build features/featurizer.py (Kafka consumer) to compute windowed features like midprice returns, bid-ask spread, trade intensity. Also build replay script, EDA notebook, and Evidently reports."
Used in: features/featurizer.py, scripts/replay.py, notebooks/eda.ipynb, scripts/generate_evidently_report.py, docs/feature_spec.md, requirements.txt
Verification: I reviewed all generated code, understood the feature engineering logic, tested the replay script, ran the EDA notebook to select threshold, and verified Evidently reports were generated successfully.

Prompt (summary): "Update requirements.txt with needed packages for Milestone 2 (pandas, pyarrow, evidently, jupyter, etc.)"
Used in: requirements.txt
Verification: I verified all packages were correctly added and installed successfully via pip install.

Prompt (summary): "Build features/featurizer.py - Kafka consumer that computes windowed features (midprice returns, bid-ask spread, trade intensity, order-book imbalance)"
Used in: features/featurizer.py
Verification: I reviewed the sliding window implementation, feature calculation logic, and verified it outputs to Kafka topic ticks.features and saves to Parquet format.

Prompt (summary): "Build scripts/replay.py - replay script to regenerate features from saved raw data identically to featurizer"
Used in: scripts/replay.py
Verification: I tested the replay script and confirmed it generates identical features to the live featurizer, ensuring reproducibility.

Prompt (summary): "Create notebooks/eda.ipynb - EDA with percentile plots to set spike threshold"
Used in: notebooks/eda.ipynb
Verification: I ran all cells in the notebook, analyzed percentile plots, and selected threshold τ = 0.000015 (99th percentile) based on the visualizations and statistics.

Prompt (summary): "Create docs/feature_spec.md with target horizon, volatility proxy, label definition, and threshold"
Used in: docs/feature_spec.md
Verification: I reviewed the specification document and updated it with the chosen threshold value (0.000015) and justification from EDA analysis.

Prompt (summary): "Set up Evidently reporting to compare early and late windows of data"
Used in: scripts/generate_evidently_report.py
Verification: I ran the script and verified it generated HTML and JSON reports showing data drift and quality metrics comparing early vs late data windows.

Prompt (summary): "Fix ws_ingest.py to also send data to Kafka (was only saving to file)"
Used in: scripts/ws_ingest.py
Verification: I verified the fix ensures data flows to both Kafka topic and local file storage.

Prompt (summary): "Update progress_tracker.md with Milestone 2 completion and threshold value"
Used in: docs/progress_tracker.md
Verification: I confirmed the tracker accurately reflects all Milestone 2 deliverables and completion status.

Prompt (summary): "Answer briefly - I just ran EDA notebook, what do I do now? Where to run generate_evidently_report.py?"
Used in: (guidance only)
Verification: I followed the step-by-step instructions to run the Evidently report generator in terminal.

Prompt (summary): "Check if threshold is in feature_spec.md and verify all Milestone 2 deliverables are complete"
Used in: docs/feature_spec.md, docs/progress_tracker.md
Verification: I verified threshold value (0.000015) is correctly documented and all deliverables are present and accounted for.

Prompt (summary): "I noticed I don't have a milestone 2 log, rather I have a milestone 2 guide. What happened?"
Used in: docs/milestone2_log.md
Verification: I identified that milestone2_guide.md was a step-by-step guide (instructions) rather than a log (accomplishments summary), created milestone2_log.md documenting all Milestone 2 achievements in the same format as milestone1_log.md and milestone3_log.md, and removed emojis per user request.

# Use of Generative AI – Milestone 3

Prompt (summary): "I've now finished Milestones 1 and 2. Please generate Milestone 3 deliverables according to the professor's rubric. Include baseline z-score model, Logistic Regression ML model, MLflow tracking, Evidently drift reports, model evaluation PDF, and model card v1."
Used in: models/baseline.py, models/train.py, models/infer.py, scripts/generate_train_test_drift_report.py, scripts/generate_model_eval_report.py, docs/model_card_v1.md, docs/milestone3_guide.md, requirements.txt
Verification: I reviewed all generated code, understood the modeling pipeline, ran training with MLflow tracking, verified models were saved, and documented results in the model card.

Prompt (summary): "How much data do we actually have? Did we just collected like 60 secs of data? Or data from the past 44 hours?"
Used in: (analysis/guidance only)
Verification: I understood that we only had 1 minute (43 samples) of data from Milestone 1, not 44 hours (which was just container uptime). This prompted data collection for Milestone 3.

Prompt (summary): "Training failed with 'No positive class found' and PR-AUC of 0. Why and how to fix?"
Used in: models/train.py, docs/feature_spec.md, docs/model_card_v1.md
Verification: I identified that the initial threshold (0.000015) from 43-sample EDA was miscalibrated for the 11,130-sample dataset, causing 98% of samples to be labeled as spikes. Re-ran EDA to find correct threshold.

Prompt (summary): "I just opened notebooks/eda.ipynb, what do I do exactly here? Need to recalculate threshold with 11,130 samples."
Used in: notebooks/eda.ipynb (re-run for new threshold)
Verification: I ran all cells in the EDA notebook, analyzed percentile plots, and identified that 99th percentile = 0.000034 and 95th percentile = 0.000028 for the updated dataset.

Prompt (summary): "With threshold 0.000034 (99th percentile), only 22 spikes total with 0 in val/test sets. Models show 0.0 test metrics. Why chronological split? How to fix?"
Used in: models/train.py, docs/feature_spec.md, docs/model_card_v1.md, docs/milestone3_log.md
Verification: I understood that chronological splits are required for time-series data to prevent leakage. The issue was too few spikes (22) concentrated in early data. Solution: Use 95th percentile (0.000028) for 557 spikes better distributed across all splits.

Prompt (summary): "Update threshold to 0.000028 (95th percentile) and update all relevant files. Document the threshold adjustment hiccups."
Used in: models/train.py, docs/feature_spec.md, docs/progress_tracker.md, docs/model_card_v1.md, docs/milestone3_log.md
Verification: I updated all threshold references across the codebase, documented the threshold selection journey, and created milestone3_log.md explaining the challenges and solutions encountered during threshold calibration.

Prompt (summary): "Help me understand what is our target variable? Also add XGBoost model and fix labeling to predict NEXT 60 seconds (forward-looking)."
Used in: models/train.py, docs/feature_spec.md, docs/model_card_v1.md, docs/milestone3_log.md
Verification: I fixed the labeling logic to use `.shift(-1)` for forward-looking predictions (predict if NEXT 60-second window will have high volatility), added XGBoost model training function with MLflow tracking, updated model comparison to include all 3 models, and updated all documentation to reflect the forward-looking prediction task. 

Prompt (summary): "Collected 20 more minutes of data, retrained models, and got new metrics. Update all documentation and explain what to do if accuracy changes."
Used in: data/raw/slice.ndjson (via `scripts/ws_ingest.py`), data/processed/features.parquet (via `scripts/replay.py`), models/train.py, docs/model_card_v1.md, docs/milestone3_log.md, docs/progress_tracker.md
Verification: I reran the replay script to regenerate features (33,881 samples), retrained baseline/Logistic Regression/XGBoost (captured in MLflow), and updated all documentation with the new dataset statistics and metrics (PR-AUC: baseline 0.9997, LR 0.7398, XGBoost 0.9997).

Prompt (summary): "Can you go through each milestone to see if I achieve 100% of what prof is asking for? My goal is to get 100 on this assignment. Let's start with milestone 2"
Used in: docs/MILESTONE2_REVIEW.md
Verification: I reviewed the assignment requirements for Milestone 2, verified all deliverables exist and function correctly, created comprehensive review document checking feature engineering pipeline, EDA notebook, threshold selection, Evidently reports, and feature specification. Identified minor discrepancy in EDA notebook (showed 99th percentile in code but 95th percentile documented in feature_spec.md) and noted it for potential update.

Prompt (summary): "how to update the notebook's final cell?"
Used in: notebooks/eda.ipynb
Verification: I updated Cell 10 in the EDA notebook to use 95th percentile (0.000028) instead of 99th percentile to match the documented threshold in feature_spec.md. Updated the code, comments, and justification text to reflect the final threshold selection decision.

Prompt (summary): "Can you go through each milestone to see if I achieve 100% of what prof is asking for? My goal is to get 100 on this assignment. Here is the extracted text from the requirement pdf: Goal: Train a model, log everything, and compare to a baseline..."
Used in: docs/MILESTONE3_REVIEW.md, models/infer.py
Verification: I reviewed all Milestone 3 requirements, verified deliverables, and identified one missing piece: latency measurement in infer.py. Added timing code to predict_batch() method to measure inference time and verify it's < 2x real-time (120 seconds). Created comprehensive review document showing 100/100 completion after the fix.

Prompt (summary): "One last very very important thing before submission: Handoff to Team Project. Create a /handoff/ folder..."
Used in: handoff/ directory (all files), handoff/HANDOFF_NOTE.md, handoff/.env.example, handoff/CHECKLIST.md
Verification: I created complete handoff package with all required files: docker files, documentation, models/artifacts, 10-minute data slice and features, reports, predictions file, and handoff note. Selected "Selected-base" approach with exact steps for team integration. Generated 10-minute data slice (6,000 records) and corresponding features, created predictions file, and wrote comprehensive handoff documentation.

Prompt (summary): "i updated the format in scoping brief doc. regenerate the pdf"
Used in: docs/scoping_brief.pdf
Verification: I regenerated the PDF from the updated scoping_brief.md using pandoc with Unicode character handling (≥ → >=, × → *, ≈ → ~=, τ → tau), verified PDF creation (131KB), and confirmed it reflects the updated formatting.
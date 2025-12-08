# MLflow Model Loading Integration

The API now loads models from MLflow instead of local pickle files, providing:
- **Reproducible experiments**: Track all model versions in MLflow
- **Controlled model versioning**: Use MODEL_VARIANT for specific versions
- **Safe rollback**: Switch models without code changes
- **Experiment tracking**: All model metadata in MLflow

## Model Loading Priority

The API loads models in this order:

1. **MLflow Model Registry** (if `MODEL_VARIANT` is set)
   - Format: `models:/model_name/stage` or `models:/model_name/version`
   - Example: `models:/xgb_model/Production` or `models:/xgb_model/1`

2. **MLflow Run ID** (if `MODEL_RUN_ID` is set)
   - Loads a specific run by ID
   - Example: `MODEL_RUN_ID=abc123def456`

3. **Latest MLflow Run** (if `MODEL_RUN_NAME` is set)
   - Searches for latest run with matching name
   - Default: `ml_xgboost`
   - Example: `MODEL_RUN_NAME=ml_xgboost`

4. **Local Pickle File** (fallback)
   - Falls back to `models/artifacts/xgb_model.pkl` if MLflow fails
   - Maintains backward compatibility

## Environment Variables

### MODEL_VARIANT
Load from MLflow Model Registry:
```bash
export MODEL_VARIANT="models:/xgb_model/Production"
# or specific version
export MODEL_VARIANT="models:/xgb_model/1"
```

### MODEL_RUN_ID
Load from specific MLflow run:
```bash
export MODEL_RUN_ID="abc123def456789"
```

### MODEL_RUN_NAME
Load from latest run with this name:
```bash
export MODEL_RUN_NAME="ml_xgboost"  # default
```

### CONFIG_PATH
Path to config file (default: `config.yaml`):
```bash
export CONFIG_PATH="/path/to/config.yaml"
```

## Registering Models in MLflow

To use Model Registry, you need to register your trained models:

### Option 1: Register via MLflow UI

1. Train your model (it will be logged to MLflow):
   ```bash
   python models/train.py --model-type xgboost
   ```

2. Go to MLflow UI: http://localhost:5000

3. Find your run (e.g., `ml_xgboost`)

4. Click on the run → "Register Model" → Create new model name (e.g., `xgb_model`)

5. Transition to stage:
   - Staging: `models:/xgb_model/Staging`
   - Production: `models:/xgb_model/Production`

### Option 2: Register via Python

Add this to your training script after logging the model:

```python
import mlflow

# After training and logging
run_id = mlflow.active_run().info.run_id
model_uri = f"runs:/{run_id}/model"

# Register model
mlflow.register_model(model_uri, "xgb_model")

# Or transition to Production
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="xgb_model",
    version=1,
    stage="Production"
)
```

## Usage Examples

### Load from Model Registry (Production)
```bash
export MODEL_VARIANT="models:/xgb_model/Production"
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
```

### Load from Latest MLflow Run
```bash
export MODEL_RUN_NAME="ml_xgboost"
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
```

### Load from Specific Run ID
```bash
export MODEL_RUN_ID="abc123def456"
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
```

### Docker Compose

Update `docker/compose.yaml` to set environment variables:

```yaml
api:
  environment:
    CONFIG_PATH: /app/config.yaml
    PORT: 8000
    MODEL_VARIANT: "models:/xgb_model/Production"  # Add this
```

## Rollback Strategy

To rollback to a previous model version:

1. **Via Model Registry**:
   ```bash
   # Transition previous version to Production
   client = mlflow.tracking.MlflowClient()
   client.transition_model_version_stage(
       name="xgb_model",
       version=2,  # Previous version
       stage="Production"
   )
   ```

2. **Via Environment Variable**:
   ```bash
   # Use specific version
   export MODEL_VARIANT="models:/xgb_model/2"
   # Restart API
   ```

3. **Via Run ID**:
   ```bash
   # Find run ID in MLflow UI
   export MODEL_RUN_ID="previous_run_id"
   # Restart API
   ```

## Benefits

✅ **No code changes needed** to switch models  
✅ **Version control** for all model deployments  
✅ **Experiment tracking** with full metadata  
✅ **Safe rollback** without redeployment  
✅ **Reproducibility** - exact model versions tracked  
✅ **A/B testing** - easy to switch between models  

## Troubleshooting

### Model not found in Registry
- Ensure model is registered: Check MLflow UI → Models
- Verify model name and stage: `models:/model_name/stage`

### No runs found
- Check experiment name in `config.yaml`
- Verify MLflow tracking URI is correct
- Ensure models were trained and logged to MLflow

### Fallback to local pickle
- If MLflow fails, API falls back to local file
- Check logs for warnings about MLflow loading failures
- Ensure `models/artifacts/xgb_model.pkl` exists

## Migration from Local Pickles

To migrate existing deployments:

1. **Register existing model**:
   ```python
   import mlflow
   import pickle
   
   # Load your existing model
   with open('models/artifacts/xgb_model.pkl', 'rb') as f:
       model = pickle.load(f)
   
   # Log to MLflow
   with mlflow.start_run():
       mlflow.sklearn.log_model(model, "model")
       run_id = mlflow.active_run().info.run_id
   
   # Register
   model_uri = f"runs:/{run_id}/model"
   mlflow.register_model(model_uri, "xgb_model")
   ```

2. **Set MODEL_VARIANT**:
   ```bash
   export MODEL_VARIANT="models:/xgb_model/Production"
   ```

3. **Restart API** - it will now load from MLflow!


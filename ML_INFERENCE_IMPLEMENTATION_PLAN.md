# ML Inference System - Implementation Plan

**Date**: August 1, 2026  
**Feature**: Complete ML Inference System  
**Status**: Ready for Implementation

---

## 🎯 Objective

Implement production-ready ML inference system for real-time fraud detection using XGBoost and Isolation Forest with SHAP explainability.

---

## 📋 Existing Architecture Analysis

### ✅ What's Already Built (REUSE - DO NOT MODIFY)

#### 1. Domain Layer - COMPLETE ✅
- `Prediction` entity with all fields needed (fraud_probability, anomaly_score, risk_score, explanation_data)
- `Model` entity for model metadata
- `PredictionClass` enum (FRAUD, LEGITIMATE)
- All validation logic built-in

#### 2. Application Layer - COMPLETE ✅  
- `PredictionService` - Full CRUD for predictions
- `Prediction DTOs` - CreatePredictionRequest, PredictionResponse, ExplanationResponse
- All use cases exist (but not wired to ML yet)

#### 3. Infrastructure/Database - COMPLETE ✅
- `PredictionRepository` - Database operations complete
- `TransactionRepository` - Transaction lookups complete
- `CustomerRepository` - Customer data complete
- `MerchantRepository` - Merchant data complete

#### 4. API Layer - EXISTS (needs completion)
- Routes folder structure exists
- Dependencies system in place
- Response wrappers ready

---

## 🚀 What Needs to be Built (NEW IMPLEMENTATION)

### Phase 1: ML Infrastructure (NEW)

#### File 1: `backend/src/infrastructure/ml/model_loader.py` (NEW)
**Purpose**: Load trained XGBoost and Isolation Forest models from disk  
**Dependencies**: xgboost, scikit-learn, joblib  
**Key Classes**:
- `ModelLoader` - Load models from filesystem/S3
- `ModelCache` - In-memory model caching
- Model validation and version checking

#### File 2: `backend/src/infrastructure/ml/feature_preprocessor.py` (NEW)
**Purpose**: Transform transaction data into ML features  
**Dependencies**: pandas, numpy  
**Key Functions**:
- Extract features from Transaction entity
- Calculate velocity metrics
- Encode categorical variables
- Handle missing values
- Feature scaling/normalization

#### File 3: `backend/src/infrastructure/ml/inference_engine.py` (NEW)
**Purpose**: Run inference with XGBoost + Isolation Forest  
**Dependencies**: xgboost, scikit-learn, numpy  
**Key Classes**:
- `FraudDetectionEngine` - Orchestrate both models
- Combine XGBoost probability with Isolation Forest anomaly score
- Calculate risk scores
- Track inference latency

#### File 4: `backend/src/infrastructure/ml/explainer.py` (NEW)
**Purpose**: Generate SHAP explanations for predictions  
**Dependencies**: shap, pandas  
**Key Classes**:
- `SHAPExplainer` - Generate explanations
- Format explanation data for API
- Top N contributing features
- Feature importance dictionary

#### File 5: `backend/src/infrastructure/ml/config.py` (NEW)
**Purpose**: ML configuration settings  
**Dependencies**: pydantic-settings  
**Key Settings**:
- Model paths (XGBoost, Isolation Forest, SHAP)
- Feature column names
- Thresholds (fraud cutoff, risk score mapping)
- Inference timeouts

---

### Phase 2: API Integration (MODIFY EXISTING)

#### File 6: `backend/src/presentation/api/v1/routes/predictions.py` (NEW - doesn't exist yet)
**Purpose**: Prediction API endpoints  
**Endpoints**:
- `POST /api/v1/predictions/predict` - Single transaction prediction
- `POST /api/v1/predictions/batch` - Batch predictions
- `GET /api/v1/predictions/{prediction_id}` - Get prediction
- `GET /api/v1/predictions/{prediction_id}/explanation` - Get explanation

#### File 7: `backend/src/presentation/api/dependencies.py` (MODIFY)
**Purpose**: Add ML dependencies  
**Changes**:
- Add `get_inference_engine()` factory
- Add `get_model_loader()` factory  
- Add `get_explainer()` factory

#### File 8: `backend/src/application/use_cases/prediction_use_cases.py` (NEW)
**Purpose**: Prediction use cases  
**Use Cases**:
- `PredictFraudUseCase` - Orchestrate inference + persistence
- `BatchPredictUseCase` - Batch inference
- `GetPredictionExplanationUseCase` - Retrieve explanation

---

### Phase 3: Testing (NEW)

#### File 9: `backend/tests/unit/infrastructure/ml/test_model_loader.py` (NEW)
**Tests**:
- Load XGBoost model
- Load Isolation Forest model
- Model caching
- Invalid model handling

#### File 10: `backend/tests/unit/infrastructure/ml/test_inference_engine.py` (NEW)
**Tests**:
- Single prediction
- Batch prediction
- Risk score calculation
- Latency tracking
- Error handling

#### File 11: `backend/tests/unit/infrastructure/ml/test_explainer.py` (NEW)
**Tests**:
- SHAP explanation generation
- Feature importance extraction
- Top N features
- Explanation formatting

#### File 12: `backend/tests/integration/test_prediction_api.py` (NEW)
**Tests**:
- End-to-end prediction API
- Explanation API
- Batch prediction API
- Error scenarios

---

### Phase 4: Configuration & Dependencies (MODIFY)

#### File 13: `backend/requirements.txt` (MODIFY)
**Add Dependencies**:
```
xgboost==2.0.3
scikit-learn==1.4.0
shap==0.44.1
pandas==2.2.0
numpy==1.26.3
joblib==1.3.2
```

#### File 14: `backend/src/config/settings.py` (MODIFY - if exists, else create)
**Add ML Settings**:
- Model paths
- Feature configurations
- Inference settings

---

## 📝 Detailed Implementation Plan

### Step 1: Add ML Dependencies
**File**: `backend/requirements.txt`  
**Action**: Append ML libraries  
**Why**: Need XGBoost, scikit-learn, SHAP for inference

### Step 2: Create ML Configuration
**File**: `backend/src/infrastructure/ml/config.py` (NEW)  
**Action**: Define `MLConfig` with Pydantic  
**Why**: Centralize ML settings, make them configurable

### Step 3: Implement Model Loader
**File**: `backend/src/infrastructure/ml/model_loader.py` (NEW)  
**Action**: Create `ModelLoader` class  
**Why**: Load trained models from disk, validate, cache in memory

### Step 4: Implement Feature Preprocessor
**File**: `backend/src/infrastructure/ml/feature_preprocessor.py` (NEW)  
**Action**: Create `FeaturePreprocessor` class  
**Why**: Transform Transaction entity → ML feature vector

### Step 5: Implement Inference Engine
**File**: `backend/src/infrastructure/ml/inference_engine.py` (NEW)  
**Action**: Create `FraudDetectionEngine` class  
**Why**: Orchestrate XGBoost + Isolation Forest inference

### Step 6: Implement SHAP Explainer
**File**: `backend/src/infrastructure/ml/explainer.py` (NEW)  
**Action**: Create `SHAPExplainer` class  
**Why**: Generate explanations for every prediction

### Step 7: Create Prediction Use Cases
**File**: `backend/src/application/use_cases/prediction_use_cases.py` (NEW)  
**Action**: Create `PredictFraudUseCase`, `BatchPredictUseCase`  
**Why**: Orchestrate inference + persistence following Clean Architecture

### Step 8: Create Prediction API Routes
**File**: `backend/src/presentation/api/v1/routes/predictions.py` (NEW)  
**Action**: Create FastAPI endpoints  
**Why**: Expose prediction functionality via REST API

### Step 9: Wire Dependencies
**File**: `backend/src/presentation/api/dependencies.py` (MODIFY)  
**Action**: Add ML dependency factories  
**Why**: Enable dependency injection for ML components

### Step 10: Write Unit Tests
**Files**: `backend/tests/unit/infrastructure/ml/*.py` (NEW)  
**Action**: Test each ML component in isolation  
**Why**: Ensure reliability, catch bugs early

### Step 11: Write Integration Tests
**File**: `backend/tests/integration/test_prediction_api.py` (NEW)  
**Action**: Test end-to-end prediction flow  
**Why**: Verify full system integration

### Step 12: Create Dummy Models for Testing
**Files**: `backend/tests/fixtures/models/` (NEW)  
**Action**: Create small trained models for testing  
**Why**: Enable testing without full model training

---

## 🔧 Implementation Scope

### IN SCOPE ✅
- XGBoost fraud classification
- Isolation Forest anomaly detection
- SHAP explainability
- Feature preprocessing
- Model loading from disk
- Real-time prediction API
- Batch prediction API
- Explanation API
- Comprehensive unit tests
- Integration tests
- Full type safety
- Configuration management
- Error handling
- Latency tracking

### OUT OF SCOPE ❌
- Model training pipeline (use pre-trained models)
- Hyperparameter optimization
- Model registry implementation
- Drift detection
- Automated retraining
- A/B testing
- AWS S3 integration (use local files for now)
- Model versioning workflow
- Performance monitoring dashboard

---

## 📂 Complete File List

### NEW FILES (12 files)
1. `backend/src/infrastructure/ml/config.py`
2. `backend/src/infrastructure/ml/model_loader.py`
3. `backend/src/infrastructure/ml/feature_preprocessor.py`
4. `backend/src/infrastructure/ml/inference_engine.py`
5. `backend/src/infrastructure/ml/explainer.py`
6. `backend/src/application/use_cases/prediction_use_cases.py`
7. `backend/src/presentation/api/v1/routes/predictions.py`
8. `backend/tests/unit/infrastructure/ml/__init__.py`
9. `backend/tests/unit/infrastructure/ml/test_model_loader.py`
10. `backend/tests/unit/infrastructure/ml/test_inference_engine.py`
11. `backend/tests/unit/infrastructure/ml/test_explainer.py`
12. `backend/tests/integration/test_prediction_api.py`

### MODIFIED FILES (2 files)
1. `backend/requirements.txt` - Add ML dependencies
2. `backend/src/presentation/api/dependencies.py` - Add ML factories

### TEST FIXTURES (3 files)
1. `backend/tests/fixtures/models/xgboost_model.json` - Dummy XGBoost model
2. `backend/tests/fixtures/models/isolation_forest_model.pkl` - Dummy IF model
3. `backend/tests/fixtures/models/shap_explainer.pkl` - Dummy SHAP explainer

**Total New Code**: ~2,000-2,500 lines  
**Total Tests**: ~800-1,000 lines

---

## 🎯 Success Criteria

### Functional Requirements ✅
1. Can load XGBoost and Isolation Forest models from disk
2. Can transform Transaction entity into ML features
3. Can make fraud predictions via `/predict` endpoint
4. Returns fraud_probability, anomaly_score, risk_score
5. Generates SHAP explanations for every prediction
6. Stores predictions in database via PredictionService
7. Handles errors gracefully (model not found, invalid input)
8. Supports batch predictions

### Performance Requirements ✅
1. Inference latency < 200ms (p95)
2. Feature preprocessing < 50ms
3. SHAP explanation < 100ms
4. Model loaded once (cached)

### Quality Requirements ✅
1. 100% type coverage
2. All unit tests pass
3. All integration tests pass
4. Ruff linting passes
5. Black formatting passes
6. mypy type checking passes
7. CI pipeline remains green

---

## 🚦 Dependencies & Blockers

### Required Before Start
- ✅ Prediction domain entities exist
- ✅ PredictionService exists
- ✅ Database repositories complete
- ✅ API infrastructure ready
- ✅ Test framework configured

### External Dependencies
- ⚠️ Need XGBoost, scikit-learn, SHAP (will add to requirements.txt)
- ⚠️ Need dummy models for testing (will create minimal models)

### No Blockers ✅
All prerequisites are met. Ready to start implementation.

---

## 📊 Estimated Impact

### Project Completion
- **Current**: 60%
- **After ML Inference**: 75%
- **Increment**: +15%

### Code Statistics
- **New Lines**: ~2,500
- **Test Lines**: ~1,000
- **Total**: ~3,500 lines

### Time Estimate
- **Implementation**: 30-35 hours
- **Testing**: 10-12 hours
- **Documentation**: 3-5 hours
- **Total**: 40-50 hours

---

## 🎬 Implementation Order

### Day 1-2: Infrastructure (8-10 hours)
1. Add dependencies to requirements.txt
2. Create ML config
3. Implement ModelLoader
4. Implement FeaturePreprocessor
5. Write unit tests for above

### Day 3-4: Inference (10-12 hours)
1. Implement InferenceEngine
2. Implement SHAPExplainer
3. Write unit tests
4. Create dummy models for testing

### Day 5-6: Application Layer (8-10 hours)
1. Create PredictionUseCases
2. Create Prediction API routes
3. Wire dependencies
4. Write integration tests

### Day 7: Polish (4-5 hours)
1. Run full test suite
2. Fix any issues
3. Verify CI passes
4. Update documentation

---

## ✅ Ready for Approval

**All prerequisites analyzed.**  
**Implementation plan complete.**  
**No architecture changes needed.**  
**Maximum code reuse identified.**

**Awaiting approval to begin implementation.**


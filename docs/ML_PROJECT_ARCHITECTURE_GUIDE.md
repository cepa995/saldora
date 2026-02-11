# Machine Learning Project Architecture Guide

A comprehensive guide to structuring ML projects with reasoning, principles, and adaptable patterns.

---

## Table of Contents

1. [The Fundamental Question](#1-the-fundamental-question)
2. [ML Project Taxonomy](#2-ml-project-taxonomy)
3. [Core Architectural Principles](#3-core-architectural-principles)
4. [The ML System Lifecycle](#4-the-ml-system-lifecycle)
5. [Component Architecture Patterns](#5-component-architecture-patterns)
6. [Data Architecture](#6-data-architecture)
7. [Model Serving Patterns](#7-model-serving-patterns)
8. [Training Infrastructure](#8-training-infrastructure)
9. [Monorepo vs Polyrepo for ML](#9-monorepo-vs-polyrepo-for-ml)
10. [When to Split Services](#10-when-to-split-services)
11. [Real-World Architecture Patterns](#11-real-world-architecture-patterns)
12. [Making Architectural Decisions](#12-making-architectural-decisions)
13. [Common Mistakes and How to Avoid Them](#13-common-mistakes-and-how-to-avoid-them)
14. [Checklist for New Projects](#14-checklist-for-new-projects)

---

## 1. The Fundamental Question

Before any architectural decision, ask yourself:

> **"What is the relationship between my ML model and my product?"**

This question determines everything. There are three fundamental relationships:

### 1.1 ML IS the Product

The model's output is directly what the user pays for.

**Examples:**
- ChatGPT (the model response IS the product)
- Midjourney (the generated image IS the product)
- GitHub Copilot (the code suggestion IS the product)

**Architectural Implications:**
- Model quality = product quality (no hiding behind UI)
- Latency is critical (users are waiting)
- You need robust fallbacks (what happens when the model fails?)
- Versioning matters enormously (users notice changes)

### 1.2 ML ENHANCES the Product

The model improves a product that would exist without it.

**Examples:**
- Netflix recommendations (you can still browse manually)
- Gmail spam filter (email works without it)
- FakturaAI (you could manually enter invoice data)

**Architectural Implications:**
- Graceful degradation is essential (product must work if ML fails)
- You can A/B test more aggressively
- User trust is earned gradually
- The "non-ML path" must always exist

### 1.3 ML ENABLES a Feature

The model powers a specific feature within a larger product.

**Examples:**
- Face detection in a photo app
- Voice search in an e-commerce site
- Fraud detection in a banking app

**Architectural Implications:**
- Feature can be toggled on/off
- Easier to iterate independently
- Can be a separate microservice
- Failure is contained to one feature

---

## 2. ML Project Taxonomy

Different ML project types have different architectural needs. Understanding this taxonomy helps you make informed decisions.

### 2.1 By Inference Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INFERENCE PATTERNS                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  REAL-TIME (Online)              BATCH (Offline)         STREAMING      │
│  ─────────────────               ──────────────          ─────────      │
│  • User is waiting               • Run periodically      • Continuous   │
│  • Latency critical              • Latency flexible      • Near-real-time│
│  • Single item inference         • Bulk processing       • Event-driven │
│  • Scale: requests/sec           • Scale: items/hour     • Scale: events/sec│
│                                                                          │
│  Examples:                       Examples:               Examples:       │
│  • Chatbots                      • Recommendation        • Fraud detection│
│  • Image classification            pre-computation       • Anomaly detection│
│  • Real-time translation         • Report generation     • Live video    │
│  • OCR processing                • Model retraining        analysis      │
│                                                                          │
│  Architecture:                   Architecture:           Architecture:   │
│  • Low-latency serving           • Job schedulers        • Stream processors│
│  • Model caching                 • Data pipelines        • Kafka/Kinesis │
│  • Load balancing                • Workflow orchestration• Stateful services│
│  • Auto-scaling                  • Airflow/Dagster       • Windowing     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Insight:** Many systems combine patterns. FakturaAI uses:
- Real-time: OCR processing when user uploads
- Batch: Model retraining on accumulated corrections
- (Potential) Streaming: SEF invoice sync

### 2.2 By Model Complexity

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MODEL COMPLEXITY SPECTRUM                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SIMPLE                    MODERATE                    COMPLEX           │
│  ──────                    ────────                    ───────           │
│                                                                          │
│  Single model              Multi-model pipeline        Ensemble/Chain    │
│  One input → One output    Sequential processing       Multiple paths    │
│  Stateless                 Some state                  Complex state     │
│                                                                          │
│  ┌─────┐                   ┌─────┐    ┌─────┐         ┌─────┐           │
│  │Model│                   │  A  │───▶│  B  │         │  A  │──┐        │
│  └─────┘                   └─────┘    └─────┘         └─────┘  │        │
│                                                          │      ▼        │
│                                                          │   ┌─────┐     │
│                                                          └──▶│Merge│     │
│                                                       ┌─────┐└─────┘     │
│                                                       │  B  │──┘         │
│                                                       └─────┘            │
│                                                                          │
│  Examples:                 Examples:                  Examples:          │
│  • Sentiment analysis      • OCR → NER → Validation   • Search ranking  │
│  • Image classification    • ASR → NLU → TTS          • Recommendation  │
│  • Spam detection          • Object detection → Track • Autonomous driving│
│                                                                          │
│  Serving:                  Serving:                   Serving:           │
│  • Single endpoint         • Pipeline orchestration   • DAG execution   │
│  • Simple scaling          • Inter-model communication• Complex routing │
│  • Easy monitoring         • Partial failure handling • A/B at each node│
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 By Data Sensitivity

| Level | Examples | Architectural Impact |
|-------|----------|---------------------|
| **Public** | Weather prediction, stock tickers | Can use cloud ML services freely |
| **Internal** | Internal analytics, employee data | Need access controls, audit logs |
| **Sensitive** | Financial data, invoices | Encryption, compliance, data residency |
| **Regulated** | Medical records, legal documents | Strict compliance (HIPAA, GDPR), on-prem options |

---

## 3. Core Architectural Principles

These principles apply to ALL ML projects, regardless of domain.

### 3.1 Separation of Concerns

**The Golden Rule:** Separate these four concerns:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     THE FOUR CONCERNS OF ML SYSTEMS                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────────┐         ┌──────────────────┐                     │
│   │   DATA LAYER     │         │   MODEL LAYER    │                     │
│   │   ────────────   │         │   ───────────    │                     │
│   │ • Ingestion      │         │ • Training       │                     │
│   │ • Storage        │         │ • Evaluation     │                     │
│   │ • Preprocessing  │         │ • Versioning     │                     │
│   │ • Feature store  │         │ • Registry       │                     │
│   └────────┬─────────┘         └────────┬─────────┘                     │
│            │                            │                                │
│            ▼                            ▼                                │
│   ┌──────────────────┐         ┌──────────────────┐                     │
│   │  SERVING LAYER   │         │ APPLICATION LAYER│                     │
│   │  ─────────────   │         │ ────────────────│                     │
│   │ • Inference API  │         │ • Business logic │                     │
│   │ • Scaling        │         │ • User interface │                     │
│   │ • Caching        │         │ • Integrations   │                     │
│   │ • Monitoring     │         │ • Workflows      │                     │
│   └──────────────────┘         └──────────────────┘                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- Each layer can evolve independently
- Different teams can own different layers
- You can swap implementations (e.g., change model without changing API)
- Easier testing (mock the model layer, test the application layer)

### 3.2 The "Offline-Online" Split

**Principle:** Anything that CAN be done offline SHOULD be done offline.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     OFFLINE vs ONLINE PROCESSING                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  OFFLINE (Pre-compute)                 ONLINE (Real-time)               │
│  ─────────────────────                 ──────────────────               │
│                                                                          │
│  ✓ Model training                      ✓ User-specific inference        │
│  ✓ Feature computation (when possible) ✓ Real-time features             │
│  ✓ Batch predictions                   ✓ Personalization                │
│  ✓ Index building                      ✓ Time-sensitive decisions       │
│  ✓ Data validation                     ✓ Interactive feedback           │
│  ✓ Embedding generation                                                  │
│                                                                          │
│  Benefits:                             Challenges:                       │
│  • Cheaper compute                     • Latency constraints            │
│  • No latency pressure                 • Scale unpredictably            │
│  • Can retry failures                  • Must handle failures gracefully│
│  • Easier debugging                    • Harder to debug                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Example - Recommendation System:**
- **Offline:** Compute item embeddings, user segments, candidate generation
- **Online:** Final ranking, real-time personalization, context-aware re-ranking

### 3.3 Graceful Degradation

**Principle:** Always have an answer, even if it's not the best answer.

```python
# BAD: Binary success/failure
def get_recommendation(user_id):
    return model.predict(user_id)  # What if this fails?

# GOOD: Graceful degradation chain
def get_recommendation(user_id):
    try:
        # Best: Personalized ML recommendation
        return ml_model.predict(user_id)
    except ModelTimeout:
        # Fallback 1: Cached recommendations
        return cache.get(f"recs:{user_id}")
    except CacheMiss:
        # Fallback 2: Popular items for user segment
        segment = get_user_segment(user_id)
        return popular_items_by_segment[segment]
    except:
        # Fallback 3: Global popular items
        return global_popular_items
```

**Degradation strategies by domain:**

| Domain | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|--------|---------|------------|------------|------------|
| OCR | ML extraction | Template matching | Manual input form | Error message |
| Search | Semantic search | Keyword search | Browse categories | Contact support |
| Translation | Neural MT | Statistical MT | Dictionary lookup | Show original |
| Recommendations | Personal ML | Segment-based | Popular items | Random sample |

### 3.4 Reproducibility

**Principle:** Any result should be reproducible given the same inputs.

This requires versioning EVERYTHING:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WHAT TO VERSION IN ML SYSTEMS                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CODE                    DATA                    MODEL                   │
│  ────                    ────                    ─────                   │
│  • Application code      • Training datasets     • Model weights         │
│  • Training scripts      • Validation datasets   • Model architecture    │
│  • Preprocessing code    • Feature definitions   • Hyperparameters       │
│  • Config files          • Data schemas          • Training metadata     │
│                                                                          │
│  Tool: Git               Tool: DVC, Delta Lake   Tool: MLflow, W&B      │
│                                                                          │
│  ENVIRONMENT             INFRASTRUCTURE                                  │
│  ───────────             ──────────────                                  │
│  • Dependencies          • Hardware specs                                │
│  • Python version        • GPU type                                      │
│  • CUDA version          • Cluster config                                │
│  • OS version            • Serving config                                │
│                                                                          │
│  Tool: Docker, Conda     Tool: Terraform, K8s manifests                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.5 Observability

**Principle:** If you can't measure it, you can't improve it.

Three pillars of ML observability:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    THREE PILLARS OF ML OBSERVABILITY                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  METRICS                 LOGS                    TRACES                  │
│  ───────                 ────                    ──────                  │
│                                                                          │
│  System Metrics:         What to log:            What to trace:          │
│  • Latency (p50/p95/p99) • Input/output samples  • Request flow          │
│  • Throughput            • Prediction confidence • Model selection       │
│  • Error rate            • Feature values        • Preprocessing steps   │
│  • GPU utilization       • Model version used    • Time per component    │
│                          • Errors with context                           │
│  ML Metrics:                                                             │
│  • Prediction distribution                                               │
│  • Feature drift                                                         │
│  • Model confidence                                                      │
│  • A/B test metrics                                                      │
│                                                                          │
│  Business Metrics:                                                       │
│  • Conversion rate                                                       │
│  • User satisfaction                                                     │
│  • Revenue impact                                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. The ML System Lifecycle

Understanding the lifecycle helps you design for the FULL journey, not just initial deployment.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ML SYSTEM LIFECYCLE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐    │
│     │  1. POC  │────▶│ 2. MVP   │────▶│ 3. PROD  │────▶│4. MATURE │    │
│     └──────────┘     └──────────┘     └──────────┘     └──────────┘    │
│                                                                          │
│     Prove it         Make it          Make it          Make it          │
│     works            usable           reliable         excellent        │
│                                                                          │
│     • Notebooks      • Basic API      • Monitoring     • A/B testing    │
│     • Local data     • Simple UI      • Scaling        • Auto-retrain   │
│     • Manual process • Basic tests    • CI/CD          • Feature store  │
│     • Single model   • Error handling • Versioning     • Multi-model    │
│                      • Documentation  • Alerting       • Self-healing   │
│                                                                          │
│     Duration:        Duration:        Duration:        Duration:         │
│     Days-Weeks       Weeks-Months     Months           Ongoing           │
│                                                                          │
│     Team: 1-2 ML     Team: ML + 1 Eng Team: ML + Eng   Team: Full stack │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Critical Insight:** Architecture should match your lifecycle stage.

| Stage | Data Storage | Model Serving | Monitoring | Team Size |
|-------|--------------|---------------|------------|-----------|
| POC | Local files, SQLite | Jupyter, local Flask | Print statements | 1-2 |
| MVP | Managed DB, S3 | Simple API server | Basic logging | 2-4 |
| Production | Data warehouse, feature store | Kubernetes, load balancer | Full observability | 4-8 |
| Mature | Data lake, streaming | Multi-region, auto-scale | ML-specific monitoring | 8+ |

**Don't over-engineer for POC. Don't under-engineer for production.**

---

## 5. Component Architecture Patterns

### 5.1 The ML Monolith

**When to use:** Early stage, small team, simple models

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ML MONOLITH                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     SINGLE APPLICATION                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐│  │
│  │  │     API     │  │   Model     │  │      Business Logic         ││  │
│  │  │   Routes    │  │  Inference  │  │      (Preprocessing,        ││  │
│  │  │             │  │             │  │       Postprocessing)        ││  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│                           ┌───────────────┐                             │
│                           │   Database    │                             │
│                           └───────────────┘                             │
│                                                                          │
│  Pros:                              Cons:                                │
│  ✓ Simple deployment               ✗ Scaling is all-or-nothing          │
│  ✓ Easy debugging                  ✗ Model updates require full deploy  │
│  ✓ Low operational overhead        ✗ Resource contention (CPU vs GPU)   │
│  ✓ Fast iteration                  ✗ Harder to test in isolation        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 The Separated Model Service

**When to use:** Model needs different scaling than API, multiple apps use the model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     SEPARATED MODEL SERVICE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────┐         ┌─────────────────────────────┐   │
│  │     APPLICATION         │         │      MODEL SERVICE          │   │
│  │  ┌─────────────────┐    │  HTTP/  │   ┌─────────────────────┐   │   │
│  │  │   API Routes    │    │  gRPC   │   │   Model Inference   │   │   │
│  │  ├─────────────────┤    │◀───────▶│   ├─────────────────────┤   │   │
│  │  │ Business Logic  │    │         │   │   Model Loading     │   │   │
│  │  ├─────────────────┤    │         │   ├─────────────────────┤   │   │
│  │  │   Pre/Post      │    │         │   │   Batching          │   │   │
│  │  │   Processing    │    │         │   └─────────────────────┘   │   │
│  │  └─────────────────┘    │         │                             │   │
│  └─────────────────────────┘         └─────────────────────────────┘   │
│              │                                     │                    │
│              ▼                                     ▼                    │
│       ┌───────────┐                        ┌───────────┐               │
│       │    DB     │                        │   Model   │               │
│       └───────────┘                        │  Storage  │               │
│                                            └───────────┘               │
│                                                                          │
│  Pros:                              Cons:                                │
│  ✓ Independent scaling             ✗ Network latency                    │
│  ✓ Model updates without app deploy✗ More infrastructure                │
│  ✓ GPU isolation                   ✗ Distributed system complexity      │
│  ✓ Multiple apps can use model     ✗ Need service discovery             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 The Pipeline Architecture

**When to use:** Complex multi-step processing, different components need different resources

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PIPELINE ARCHITECTURE                               │
│                     (e.g., FakturaAI OCR Pipeline)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐   │
│  │ Ingest │───▶│Preproc │───▶│  OCR   │───▶│  NER   │───▶│ Output │   │
│  │        │    │        │    │        │    │        │    │        │   │
│  │  CPU   │    │  CPU   │    │  GPU   │    │  CPU   │    │  CPU   │   │
│  │  Fast  │    │  Fast  │    │  Slow  │    │  Med   │    │  Fast  │   │
│  └────────┘    └────────┘    └────────┘    └────────┘    └────────┘   │
│       │             │             │             │             │         │
│       └─────────────┴─────────────┴─────────────┴─────────────┘         │
│                                   │                                      │
│                                   ▼                                      │
│                          ┌───────────────┐                              │
│                          │  Task Queue   │                              │
│                          │   (Celery)    │                              │
│                          └───────────────┘                              │
│                                                                          │
│  Orchestration Options:                                                  │
│  • Task Queue (Celery) - Simple, good for async jobs                    │
│  • Workflow Engine (Airflow, Dagster) - Complex DAGs, scheduling        │
│  • Stream Processing (Kafka) - Real-time, high throughput               │
│  • Serverless (Step Functions) - Event-driven, auto-scale               │
│                                                                          │
│  Key Decisions:                                                          │
│  • Where to checkpoint (save intermediate results)?                     │
│  • How to handle partial failures?                                      │
│  • Sync vs async between steps?                                         │
│  • How to scale each step independently?                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.4 The Ensemble/Router Architecture

**When to use:** Multiple models for different scenarios, A/B testing, gradual rollout

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ENSEMBLE/ROUTER ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                         ┌───────────────┐                               │
│                         │    Router     │                               │
│                         │   (decides    │                               │
│                         │ which model)  │                               │
│                         └───────┬───────┘                               │
│                                 │                                        │
│              ┌──────────────────┼──────────────────┐                    │
│              ▼                  ▼                  ▼                    │
│       ┌───────────┐      ┌───────────┐      ┌───────────┐              │
│       │  Model A  │      │  Model B  │      │  Model C  │              │
│       │  (v1.0)   │      │  (v2.0)   │      │ (special) │              │
│       │   90%     │      │   10%     │      │  rules    │              │
│       └─────┬─────┘      └─────┬─────┘      └─────┬─────┘              │
│             │                  │                  │                     │
│             └──────────────────┼──────────────────┘                     │
│                                ▼                                        │
│                         ┌───────────────┐                               │
│                         │   Combiner    │                               │
│                         │  (optional)   │                               │
│                         └───────────────┘                               │
│                                                                          │
│  Router Strategies:                                                      │
│  • Traffic split (A/B testing)                                          │
│  • Feature-based (different model for different inputs)                 │
│  • Cascade (try cheap model first, escalate if uncertain)               │
│  • Ensemble (combine multiple model outputs)                            │
│                                                                          │
│  Example - Cascade:                                                      │
│  1. Rule-based check (instant, free)                                    │
│  2. Small model (fast, cheap)                                           │
│  3. Large model (slow, expensive) - only if small model uncertain       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Data Architecture

Data architecture is often MORE important than model architecture.

### 6.1 The Data Gravity Problem

**Principle:** Data has gravity - it's expensive to move.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA GRAVITY                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  "Move compute to data, not data to compute"                            │
│                                                                          │
│  BAD:                                                                    │
│  ┌─────────┐     100GB/day      ┌─────────┐                            │
│  │  Data   │───────────────────▶│ Compute │   Cost: $$$, Latency: High │
│  │ (Cloud) │                    │ (Local) │                             │
│  └─────────┘                    └─────────┘                             │
│                                                                          │
│  GOOD:                                                                   │
│  ┌─────────────────────────────────────────┐                            │
│  │              Same Region                 │                            │
│  │  ┌─────────┐           ┌─────────┐      │   Cost: $, Latency: Low   │
│  │  │  Data   │◀─────────▶│ Compute │      │                            │
│  │  └─────────┘           └─────────┘      │                            │
│  └─────────────────────────────────────────┘                            │
│                                                                          │
│  Implications for ML:                                                    │
│  • Train where data lives                                               │
│  • Consider data residency requirements (GDPR, local laws)              │
│  • Batch data transfers during off-peak hours                           │
│  • Use data versioning, not data copying                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Training Data vs Serving Data

**Critical distinction:** The path data takes for training is different from serving.

```
┌─────────────────────────────────────────────────────────────────────────┐
│              TRAINING DATA vs SERVING DATA                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TRAINING PATH:                                                          │
│  ─────────────                                                           │
│  Raw Data → Clean → Transform → Feature Engineer → Store → Train        │
│      │         │          │              │                               │
│      │    (batch)    (batch)        (batch)                             │
│      │                                                                   │
│      └─── Historical data, can reprocess, offline                       │
│                                                                          │
│  SERVING PATH:                                                           │
│  ─────────────                                                           │
│  Request → Extract Features → Model → Response                          │
│      │            │                                                      │
│      │      (real-time)                                                  │
│      │                                                                   │
│      └─── Live data, must be fast, online                               │
│                                                                          │
│  THE PROBLEM: Training-Serving Skew                                      │
│  ────────────────────────────────────                                    │
│  If training features != serving features, model performs poorly         │
│                                                                          │
│  SOLUTION: Feature Store                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                       FEATURE STORE                              │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │    │
│  │  │  Feature    │    │  Feature    │    │   Feature           │  │    │
│  │  │ Definitions │───▶│  Compute    │───▶│   Storage           │  │    │
│  │  │  (code)     │    │  (offline)  │    │  (online + offline) │  │    │
│  │  └─────────────┘    └─────────────┘    └──────────┬──────────┘  │    │
│  │                                                   │              │    │
│  │                    ┌──────────────────────────────┴───────┐     │    │
│  │                    ▼                                      ▼     │    │
│  │             ┌─────────────┐                      ┌─────────────┐│    │
│  │             │  Training   │                      │   Serving   ││    │
│  │             │   (batch)   │                      │  (real-time)││    │
│  │             └─────────────┘                      └─────────────┘│    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Feature Store Options: Feast, Tecton, Hopsworks, AWS SageMaker FS      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Data Lake vs Data Warehouse vs Feature Store

| Aspect | Data Lake | Data Warehouse | Feature Store |
|--------|-----------|----------------|---------------|
| **Purpose** | Store everything | Business analytics | ML features |
| **Schema** | Schema-on-read | Schema-on-write | Strongly typed |
| **Users** | Data engineers | Analysts, BI | ML engineers |
| **Query pattern** | Batch, exploration | Batch, reporting | Point lookups, batch |
| **Format** | Raw (JSON, Parquet) | Structured tables | Key-value, time series |
| **Tools** | S3, Delta Lake, Iceberg | Snowflake, BigQuery, Redshift | Feast, Tecton |

**When do you need a Feature Store?**
- Multiple models share features
- Training-serving skew is causing problems
- Feature computation is expensive and should be cached
- You need point-in-time correctness for training

---

## 7. Model Serving Patterns

### 7.1 Serving Options Comparison

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MODEL SERVING OPTIONS                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  EMBEDDED                 MICROSERVICE              SERVERLESS          │
│  ────────                 ────────────              ──────────          │
│                                                                          │
│  Model loaded in          Model in separate         Model in cloud      │
│  application process      service                   function            │
│                                                                          │
│  ┌─────────┐              ┌─────────┐    ┌─────┐   ┌─────────────────┐ │
│  │   App   │              │   App   │───▶│Model│   │   Lambda/Cloud  │ │
│  │ + Model │              └─────────┘    │ Svc │   │   Function      │ │
│  └─────────┘                             └─────┘   │   + Model       │ │
│                                                     └─────────────────┘ │
│                                                                          │
│  Pros:                    Pros:                     Pros:               │
│  • No network latency     • Independent scaling     • Auto-scaling      │
│  • Simple deployment      • Multiple consumers      • Pay-per-use       │
│  • Single failure domain  • Isolated resources      • No infra mgmt     │
│                                                                          │
│  Cons:                    Cons:                     Cons:               │
│  • Resource contention    • Network latency         • Cold starts       │
│  • Hard to update model   • More infrastructure     • Size limits       │
│  • Can't scale separately • Distributed system      • Vendor lock-in    │
│                                                                          │
│  Best for:                Best for:                 Best for:           │
│  • Small models           • Large/GPU models        • Spiky traffic     │
│  • Low traffic            • Multiple apps need it   • Prototype/MVP     │
│  • Simple use cases       • Complex pipelines       • Cost optimization │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Batching Strategies

**Why batching matters:** GPUs are efficient at parallel processing. A batch of 32 might take only 1.5x the time of a single item.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       BATCHING STRATEGIES                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  NO BATCHING                      CLIENT-SIDE BATCHING                  │
│  ───────────                      ────────────────────                  │
│                                                                          │
│  Request → Process → Response     Requests → Collect → Batch Process   │
│                                                                          │
│  Latency: Predictable             Latency: Variable (wait for batch)   │
│  Throughput: Low                  Throughput: Higher                    │
│                                   Good for: Batch jobs, non-interactive │
│                                                                          │
│  SERVER-SIDE DYNAMIC BATCHING     ADAPTIVE BATCHING                     │
│  ────────────────────────────     ─────────────────                     │
│                                                                          │
│  ┌─────────────────────────┐     Adjust batch size based on:           │
│  │    Request Queue        │     • Current latency                      │
│  │  [r1] [r2] [r3] [r4]    │     • Queue depth                         │
│  └───────────┬─────────────┘     • GPU memory                          │
│              │                    • Model characteristics               │
│              ▼                                                          │
│  ┌─────────────────────────┐     ┌─────────────────────────────────┐   │
│  │  Wait for:              │     │  if queue_depth > threshold:    │   │
│  │  • max_batch_size OR    │     │      batch_size = max_batch     │   │
│  │  • max_wait_time        │     │  elif latency > target:         │   │
│  │  (whichever first)      │     │      batch_size = min_batch     │   │
│  └─────────────────────────┘     │  else:                          │   │
│                                   │      batch_size = optimal       │   │
│  Latency: Bounded                 └─────────────────────────────────┘   │
│  Throughput: High                                                        │
│  Good for: Real-time services                                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Caching Strategies

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       ML CACHING STRATEGIES                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  WHAT TO CACHE                    WHERE TO CACHE                        │
│  ─────────────                    ──────────────                        │
│                                                                          │
│  ✓ Model outputs                  Application level:                    │
│    (if same input = same output)  └─ In-memory dict, LRU cache         │
│                                                                          │
│  ✓ Intermediate features          Service level:                        │
│    (expensive to compute)         └─ Redis, Memcached                   │
│                                                                          │
│  ✓ Embeddings                     Disk level:                           │
│    (reused across requests)       └─ Local SSD, shared storage          │
│                                                                          │
│  ✗ Don't cache if:                CDN level:                            │
│    • Output depends on time       └─ Cloudflare, CloudFront             │
│    • Personalization required       (for static model artifacts)        │
│    • Model is being A/B tested                                          │
│                                                                          │
│  CACHE KEY DESIGN                                                        │
│  ────────────────                                                        │
│                                                                          │
│  key = hash(                                                             │
│      input_data,                  # The actual input                    │
│      model_version,               # CRITICAL: include version!          │
│      preprocessing_version,       # If preprocessing changed            │
│      feature_flags                # A/B test variant                    │
│  )                                                                       │
│                                                                          │
│  Cache invalidation triggers:                                            │
│  • Model version change                                                 │
│  • Feature definition change                                            │
│  • TTL expiration                                                       │
│  • Manual purge                                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Training Infrastructure

### 8.1 Training Environments

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TRAINING ENVIRONMENTS                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LOCAL                    CLOUD VMs               MANAGED ML PLATFORMS  │
│  ─────                    ────────               ────────────────────   │
│                                                                          │
│  Your laptop/workstation  EC2, GCE, Azure VMs    SageMaker, Vertex AI   │
│                                                   Databricks, Anyscale   │
│  Pros:                    Pros:                  Pros:                   │
│  • Fast iteration         • Flexible             • Integrated tooling   │
│  • No cloud costs         • Scale up/down        • Experiment tracking  │
│  • Full control           • GPU access           • Managed infra        │
│                                                                          │
│  Cons:                    Cons:                  Cons:                   │
│  • Limited resources      • Ops overhead         • Expensive            │
│  • Not reproducible       • Spot instance mgmt   • Vendor lock-in       │
│  • No collaboration       • Manual scaling       • Less flexibility     │
│                                                                          │
│  Best for:                Best for:              Best for:               │
│  • Prototyping            • Custom requirements  • Enterprise teams     │
│  • Small models           • Cost optimization    • Quick start          │
│  • Quick experiments      • Large-scale training • Compliance needs     │
│                                                                          │
│  HYBRID APPROACH (Recommended for most teams):                          │
│  ─────────────────────────────────────────────                          │
│  • Local: Quick experiments, debugging                                  │
│  • Cloud VMs: Serious training, hyperparameter search                   │
│  • Managed: Production pipelines, scheduled retraining                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Experiment Tracking

**What to track:**

```python
# For EVERY training run, log:
experiment.log({
    # Inputs
    "dataset_version": "v2.3.1",
    "dataset_size": 50000,
    "features_used": ["f1", "f2", "f3"],

    # Configuration
    "model_type": "transformer",
    "hyperparameters": {
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 10,
        "hidden_size": 256
    },

    # Environment
    "git_commit": "abc123",
    "python_version": "3.11",
    "pytorch_version": "2.0",
    "gpu_type": "A100",

    # Outputs
    "metrics": {
        "train_loss": 0.05,
        "val_loss": 0.08,
        "val_accuracy": 0.95,
        "inference_latency_p95": 45  # ms
    },

    # Artifacts
    "model_path": "s3://models/exp-123/model.pt",
    "confusion_matrix": wandb.Image(...),
    "sample_predictions": wandb.Table(...)
})
```

**Tools:** MLflow, Weights & Biases, Neptune, Comet

### 8.3 Training Pipeline Patterns

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TRAINING PIPELINE PATTERNS                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  MANUAL TRAINING                   SCHEDULED RETRAINING                  │
│  ───────────────                   ────────────────────                  │
│                                                                          │
│  Data Scientist runs               Cron/Airflow triggers                │
│  training notebook                 training pipeline                    │
│                                                                          │
│  Best for: R&D, exploration        Best for: Stable models,             │
│                                    regular data updates                  │
│                                                                          │
│  TRIGGERED RETRAINING              CONTINUOUS TRAINING                   │
│  ────────────────────              ────────────────────                  │
│                                                                          │
│  Events trigger training:          Always training on                   │
│  • Data drift detected             streaming data                       │
│  • Performance degradation                                               │
│  • New data volume threshold       Best for: Fast-changing              │
│                                    environments, real-time              │
│  Best for: Dynamic environments    personalization                      │
│                                                                          │
│                                                                          │
│  TYPICAL ENTERPRISE PATTERN:                                             │
│  ───────────────────────────                                             │
│                                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  Data    │───▶│ Feature  │───▶│  Train   │───▶│ Evaluate │          │
│  │ Ingest   │    │  Compute │    │  Model   │    │  Model   │          │
│  └──────────┘    └──────────┘    └──────────┘    └─────┬────┘          │
│                                                        │                 │
│                   ┌──────────────────────────────────┬─┘                 │
│                   ▼                                  ▼                   │
│  ┌──────────────────────────┐          ┌──────────────────────┐         │
│  │  Passes validation?      │          │  Fails validation    │         │
│  │  ─────────────────       │          │  ────────────────    │         │
│  │  ┌──────────┐            │          │  • Alert team        │         │
│  │  │ Register │            │          │  • Log failure       │         │
│  │  │ Model    │            │          │  • Keep old model    │         │
│  │  └────┬─────┘            │          └──────────────────────┘         │
│  │       │                  │                                            │
│  │       ▼                  │                                            │
│  │  ┌──────────┐            │                                            │
│  │  │ A/B Test │            │                                            │
│  │  │ (shadow) │            │                                            │
│  │  └────┬─────┘            │                                            │
│  │       │                  │                                            │
│  │       ▼                  │                                            │
│  │  ┌──────────┐            │                                            │
│  │  │ Gradual  │            │                                            │
│  │  │ Rollout  │            │                                            │
│  │  └──────────┘            │                                            │
│  └──────────────────────────┘                                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Monorepo vs Polyrepo for ML

### 9.1 The Decision Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MONOREPO vs POLYREPO                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  MONOREPO                          POLYREPO                             │
│  ────────                          ────────                             │
│                                                                          │
│  faktura-ai/                       faktura-web/                         │
│  ├── apps/                         faktura-api/                         │
│  │   ├── web/                      faktura-ml/                          │
│  │   └── api/                      faktura-common/                      │
│  ├── packages/                                                          │
│  │   ├── shared/                                                        │
│  │   └── ml-models/                                                     │
│  └── workers/                                                           │
│      └── ml/                                                            │
│                                                                          │
│  Pros:                             Pros:                                │
│  ✓ Atomic changes across services  ✓ Clear ownership                   │
│  ✓ Shared code is easy             ✓ Independent versioning            │
│  ✓ Unified CI/CD                   ✓ Smaller repos, faster git         │
│  ✓ Easier refactoring              ✓ Team autonomy                     │
│  ✓ Single source of truth          ✓ Technology flexibility            │
│                                                                          │
│  Cons:                             Cons:                                │
│  ✗ Large repo, slow git            ✗ Dependency hell                   │
│  ✗ Complex CI/CD                   ✗ Cross-repo changes are hard       │
│  ✗ Harder to enforce boundaries    ✗ Code duplication                  │
│  ✗ Everyone sees everything        ✗ Integration testing harder        │
│                                                                          │
│  Best for:                         Best for:                            │
│  • Startups, small teams           • Large orgs, many teams            │
│  • Tightly coupled services        • Independent deployables           │
│  • Rapid iteration                 • Different release cycles          │
│  • Shared ML components            • Outsourced components             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 ML-Specific Considerations

**Monorepo advantages for ML:**
1. **Shared preprocessing code** - Same transformations for training and serving
2. **Type consistency** - Shared schemas between API and ML
3. **Atomic model updates** - Update model + API contract together
4. **Unified testing** - Integration tests across the full pipeline

**Polyrepo might be better when:**
1. **ML team is separate** - Different release cycles, different skills
2. **Models are large** - Git struggles with large binary files
3. **Multiple products** - Different products use same model
4. **Compliance requirements** - ML code needs different access controls

### 9.3 Recommended Structure (Monorepo with ML)

```
project/
├── apps/                           # Deployable applications
│   ├── web/                        # Frontend (Next.js, React)
│   │   ├── src/
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   └── api/                        # Backend API (FastAPI, Express)
│       ├── src/
│       ├── requirements.txt
│       └── Dockerfile
│
├── packages/                       # Shared libraries
│   ├── shared-types/               # TypeScript types, Pydantic models
│   │   └── schemas/
│   │
│   ├── ml-core/                    # ML utilities, feature engineering
│   │   ├── preprocessing/
│   │   ├── postprocessing/
│   │   └── evaluation/
│   │
│   └── db/                         # Database models, migrations
│       └── migrations/
│
├── workers/                        # Background job processors
│   └── ml-worker/                  # Celery/RQ workers for ML inference
│       ├── tasks/
│       └── Dockerfile
│
├── ml/                             # ML-specific (can be separate repo)
│   ├── notebooks/                  # Exploration, prototyping
│   │   └── experiments/
│   │
│   ├── training/                   # Training pipelines
│   │   ├── configs/
│   │   ├── scripts/
│   │   └── Dockerfile.training
│   │
│   ├── models/                     # Model definitions
│   │   ├── ocr/
│   │   ├── ner/
│   │   └── classification/
│   │
│   ├── evaluation/                 # Evaluation scripts, benchmarks
│   │   ├── benchmarks/
│   │   └── reports/
│   │
│   └── data/                       # Data versioning (DVC)
│       ├── raw/
│       ├── processed/
│       └── dvc.yaml
│
├── infra/                          # Infrastructure as code
│   ├── terraform/
│   ├── kubernetes/
│   └── docker-compose.yml
│
├── scripts/                        # Development utilities
│   ├── setup.sh
│   └── deploy.sh
│
├── tests/                          # Cross-package integration tests
│   └── e2e/
│
└── docs/
    ├── architecture.md
    └── ml-guide.md
```

---

## 10. When to Split Services

### 10.1 The Decision Matrix

```
┌─────────────────────────────────────────────────────────────────────────┐
│              WHEN TO SPLIT: DECISION MATRIX                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  KEEP TOGETHER IF:                 SPLIT IF:                            │
│  ─────────────────                 ─────────                            │
│                                                                          │
│  □ Same scaling requirements       ☑ Different scaling (CPU vs GPU)    │
│  □ Same team owns both             ☑ Different teams                   │
│  □ Tight coupling (shared state)   ☑ Loose coupling (API only)         │
│  □ Same release cycle              ☑ Independent releases              │
│  □ Low traffic                     ☑ High traffic, need isolation      │
│  □ Prototype/MVP stage             ☑ Production, need reliability      │
│  □ Small model, fast inference     ☑ Large model, GPU required         │
│                                                                          │
│                                                                          │
│  SPLIT SIGNALS (Red Flags):                                              │
│  ──────────────────────────                                              │
│                                                                          │
│  1. "We can't deploy the API because ML training is broken"             │
│     → Split: API and training are different concerns                    │
│                                                                          │
│  2. "API is slow because ML inference is hogging resources"             │
│     → Split: Different resource profiles                                │
│                                                                          │
│  3. "ML team has to wait for API team to deploy their model"            │
│     → Split: Independent deployment                                     │
│                                                                          │
│  4. "We need more GPU workers but not more API servers"                 │
│     → Split: Independent scaling                                        │
│                                                                          │
│  5. "Model crash takes down the whole application"                      │
│     → Split: Fault isolation                                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Common Split Points

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMMON SERVICE BOUNDARIES                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TYPICAL EVOLUTION:                                                      │
│                                                                          │
│  Stage 1: Monolith                                                       │
│  ┌────────────────────────────────┐                                     │
│  │  [API + Business Logic + ML]  │                                     │
│  └────────────────────────────────┘                                     │
│                                                                          │
│  Stage 2: Extract ML Worker (async processing)                          │
│  ┌────────────────────┐    ┌────────────────┐                          │
│  │  [API + Business]  │◀──▶│  [ML Worker]   │                          │
│  └────────────────────┘    └────────────────┘                          │
│           │                        │                                     │
│           └────────┬───────────────┘                                     │
│                    ▼                                                     │
│             [Task Queue]                                                 │
│                                                                          │
│  Stage 3: ML as Separate Service (sync)                                 │
│  ┌────────────────────┐    ┌────────────────┐                          │
│  │  [API + Business]  │───▶│  [ML Service]  │                          │
│  └────────────────────┘    └────────────────┘                          │
│                                                                          │
│  Stage 4: Full Separation                                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│  │   API   │  │Business │  │   ML    │  │  Data   │                   │
│  │ Gateway │  │  Logic  │  │ Service │  │Pipeline │                   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘                   │
│                                                                          │
│                                                                          │
│  RECOMMENDED BOUNDARIES:                                                 │
│  ───────────────────────                                                 │
│                                                                          │
│  1. Preprocessing from Inference                                        │
│     Why: Preprocessing is usually CPU, inference may need GPU           │
│                                                                          │
│  2. Training from Serving                                               │
│     Why: Completely different lifecycles and resource needs             │
│                                                                          │
│  3. Real-time from Batch                                                │
│     Why: Different latency requirements, different scaling              │
│                                                                          │
│  4. Business Logic from ML                                              │
│     Why: Business logic changes frequently, ML changes carefully        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Real-World Architecture Patterns

### 11.1 Pattern: Document Processing SaaS (FakturaAI style)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 DOCUMENT PROCESSING ARCHITECTURE                         │
│                 (OCR, Invoice Processing, etc.)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  USER FLOW:                                                              │
│  Upload → Process → Review → Export                                     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         USER INTERFACE                           │   │
│  │  • Upload with preview    • Side-by-side review                 │   │
│  │  • Progress indication    • Field confidence display            │   │
│  │  • Batch management       • Export options                      │   │
│  └────────────────────────────────────┬────────────────────────────┘   │
│                                       │                                  │
│                                       ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        API LAYER                                 │   │
│  │  • Document upload         • Status polling                     │   │
│  │  • Job management          • Export generation                  │   │
│  │  • User/org management     • Webhook delivery                   │   │
│  └────────────────────────────────┬────────────────────────────────┘   │
│                                   │                                      │
│           ┌───────────────────────┼───────────────────────┐             │
│           ▼                       ▼                       ▼             │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │
│  │  Document       │   │   ML Pipeline   │   │   Export        │       │
│  │  Storage        │   │   (Async)       │   │   Service       │       │
│  │                 │   │                 │   │                 │       │
│  │  • Upload       │   │  ┌───────────┐  │   │  • Templates    │       │
│  │  • CDN delivery │   │  │ Preprocess│  │   │  • Formatting   │       │
│  │  • Versioning   │   │  └─────┬─────┘  │   │  • Validation   │       │
│  └─────────────────┘   │        ▼        │   └─────────────────┘       │
│                        │  ┌───────────┐  │                              │
│                        │  │    OCR    │  │   ┌─────────────────┐       │
│                        │  │   (GPU)   │  │   │  External APIs  │       │
│                        │  └─────┬─────┘  │   │                 │       │
│                        │        ▼        │   │  • APR verify   │       │
│                        │  ┌───────────┐  │   │  • SEF sync     │       │
│                        │  │    NER    │  │   │  • Payment      │       │
│                        │  └─────┬─────┘  │   └─────────────────┘       │
│                        │        ▼        │                              │
│                        │  ┌───────────┐  │                              │
│                        │  │ Validate  │  │                              │
│                        │  └───────────┘  │                              │
│                        └─────────────────┘                              │
│                                                                          │
│  KEY DECISIONS:                                                          │
│  • Async processing (users don't wait for OCR)                          │
│  • Confidence scoring on all fields                                     │
│  • Human-in-the-loop for low confidence                                 │
│  • Feedback loop to improve models                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Pattern: Real-time Recommendation System

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 RECOMMENDATION SYSTEM ARCHITECTURE                       │
│                 (E-commerce, Content, etc.)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      OFFLINE PATH (Batch)                         │  │
│  │                                                                    │  │
│  │  ┌────────┐   ┌────────────┐   ┌────────────┐   ┌─────────────┐  │  │
│  │  │ Event  │──▶│  Feature   │──▶│   Train    │──▶│   Store     │  │  │
│  │  │  Log   │   │  Compute   │   │   Models   │   │   Embeddings│  │  │
│  │  └────────┘   └────────────┘   └────────────┘   └─────────────┘  │  │
│  │     │                                                  │          │  │
│  │     │              Runs: Daily/Weekly                  │          │  │
│  └─────┼──────────────────────────────────────────────────┼──────────┘  │
│        │                                                  │              │
│        │                                                  ▼              │
│  ┌─────┼─────────────────────────────────────────────────────────────┐  │
│  │     │             ONLINE PATH (Real-time)                         │  │
│  │     │                                                             │  │
│  │     ▼                                                             │  │
│  │  ┌────────┐   ┌────────────┐   ┌────────────┐   ┌─────────────┐  │  │
│  │  │Request │──▶│  Candidate │──▶│   Rank     │──▶│   Filter    │  │  │
│  │  │+ Context│  │  Retrieval │   │   (ML)     │   │   & Return  │  │  │
│  │  └────────┘   └────────────┘   └────────────┘   └─────────────┘  │  │
│  │                     │                │                            │  │
│  │               Uses embeddings   Real-time                         │  │
│  │               from offline      personalization                   │  │
│  │                                                                   │  │
│  │     Latency budget: ~50ms                                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  SCALING STRATEGY:                                                       │
│  • Pre-compute item embeddings (offline)                                │
│  • ANN index for fast retrieval (FAISS, Milvus)                         │
│  • Small ranking model for real-time                                    │
│  • Cache popular user segments                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.3 Pattern: Computer Vision API

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMPUTER VISION API ARCHITECTURE                      │
│                    (Object Detection, Classification, etc.)              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         API GATEWAY                               │  │
│  │  • Rate limiting      • Authentication                           │  │
│  │  • Request validation • Usage tracking                           │  │
│  └────────────────────────────────┬─────────────────────────────────┘  │
│                                   │                                      │
│                                   ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      PREPROCESSING SERVICE                        │  │
│  │  • Image decoding     • Resize/normalize                         │  │
│  │  • Format validation  • Quality check                            │  │
│  └────────────────────────────────┬─────────────────────────────────┘  │
│                                   │                                      │
│                                   ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       MODEL ROUTER                                │  │
│  │                                                                    │  │
│  │   Request type? ────┬─────────────┬─────────────┬───────────     │  │
│  │                     ▼             ▼             ▼                 │  │
│  │              ┌───────────┐ ┌───────────┐ ┌───────────┐           │  │
│  │              │ Detection │ │  Classif  │ │Segmentation│          │  │
│  │              │  Model    │ │  Model    │ │   Model   │           │  │
│  │              │  (YOLO)   │ │  (ResNet) │ │  (U-Net)  │           │  │
│  │              └───────────┘ └───────────┘ └───────────┘           │  │
│  │                                                                    │  │
│  │   GPU Pool: Auto-scaling based on queue depth                    │  │
│  │   Batching: Dynamic, max wait 50ms                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  SCALING CONSIDERATIONS:                                                 │
│  • GPU instances are expensive - maximize utilization via batching      │
│  • Use spot/preemptible instances for cost savings                      │
│  • Cache results for identical images (hash-based)                      │
│  • Consider model distillation for latency-critical paths               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Making Architectural Decisions

### 12.1 The Decision Framework

When faced with an architectural decision, work through these questions:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURAL DECISION FRAMEWORK                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. WHAT PROBLEM ARE WE SOLVING?                                        │
│     ───────────────────────────                                         │
│     • Write it down in one sentence                                     │
│     • If you can't, you don't understand it yet                         │
│                                                                          │
│  2. WHAT ARE THE CONSTRAINTS?                                           │
│     ────────────────────────                                            │
│     • Latency requirements                                              │
│     • Throughput requirements                                           │
│     • Budget (compute, team, time)                                      │
│     • Compliance/security requirements                                   │
│     • Team skills and size                                              │
│     • Existing infrastructure                                           │
│                                                                          │
│  3. WHAT ARE THE OPTIONS?                                               │
│     ─────────────────────                                               │
│     • List at least 3 options (including "do nothing")                  │
│     • For each, list pros/cons                                          │
│     • Consider the simplest option first                                │
│                                                                          │
│  4. WHAT ARE THE TRADE-OFFS?                                            │
│     ───────────────────────                                             │
│     • What do we gain?                                                  │
│     • What do we give up?                                               │
│     • What are the risks?                                               │
│     • Is this reversible?                                               │
│                                                                          │
│  5. HOW WILL WE KNOW IF IT'S WORKING?                                   │
│     ─────────────────────────────────                                   │
│     • Define success metrics BEFORE implementing                        │
│     • Include operational metrics (latency, errors)                     │
│     • Include business metrics (conversion, satisfaction)               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Decision Record Template

For every significant decision, document it:

```markdown
# ADR-001: [Decision Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or more difficult to do because of this change?

## Alternatives Considered
What other options did we consider and why did we reject them?

## References
- [Link to relevant docs]
- [Link to discussion]
```

### 12.3 Common Trade-offs

| Trade-off | When to favor A | When to favor B |
|-----------|-----------------|-----------------|
| **Latency vs Cost** | User-facing, real-time | Batch, internal tools |
| **Accuracy vs Speed** | High-stakes decisions | Exploration, suggestions |
| **Flexibility vs Simplicity** | Mature product, clear requirements | Early stage, uncertain requirements |
| **Build vs Buy** | Core competency, competitive advantage | Commodity, not differentiating |
| **Monolith vs Services** | Small team, fast iteration | Large team, independent scaling |
| **GPU vs CPU** | Large models, parallel work | Small models, low traffic |

---

## 13. Common Mistakes and How to Avoid Them

### 13.1 Architecture Anti-Patterns

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ML ARCHITECTURE ANTI-PATTERNS                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. THE "ML WILL FIX IT" TRAP                                           │
│     ───────────────────────────                                         │
│     Problem: Using ML when rules would suffice                          │
│     Example: ML model to check if email contains "@"                    │
│     Solution: Start with rules, add ML for fuzzy cases                  │
│                                                                          │
│  2. THE "NOTEBOOK TO PRODUCTION" DISASTER                               │
│     ───────────────────────────────────────                             │
│     Problem: Deploying Jupyter notebooks directly                       │
│     Symptoms: Hidden state, no tests, unreproducible                   │
│     Solution: Refactor to modules, add tests, use proper serving       │
│                                                                          │
│  3. THE "BIG BANG DEPLOYMENT"                                           │
│     ─────────────────────────                                           │
│     Problem: Replacing old model 100% at once                          │
│     Risk: New model might be worse in production                       │
│     Solution: Gradual rollout, shadow mode, A/B testing                │
│                                                                          │
│  4. THE "TRAINING-SERVING SKEW" KILLER                                  │
│     ───────────────────────────────────                                 │
│     Problem: Different preprocessing in training vs serving            │
│     Symptoms: Model works in dev, fails in prod                        │
│     Solution: Shared preprocessing code, feature store                 │
│                                                                          │
│  5. THE "NO FEEDBACK LOOP" BLINDSPOT                                    │
│     ─────────────────────────────────                                   │
│     Problem: Deploying model and never improving it                    │
│     Result: Model degrades over time (data drift)                      │
│     Solution: Monitor, collect feedback, retrain pipeline              │
│                                                                          │
│  6. THE "OVER-ENGINEERING" TRAP                                         │
│     ─────────────────────────────                                       │
│     Problem: Building for scale you don't have                         │
│     Example: Kubernetes + feature store + MLflow for 10 users          │
│     Solution: YAGNI - add complexity when needed                       │
│                                                                          │
│  7. THE "UNDER-ENGINEERING" DEBT                                        │
│     ───────────────────────────────                                     │
│     Problem: Taking shortcuts that compound                            │
│     Example: Hardcoded paths, no versioning, no monitoring             │
│     Solution: Invest in basics early (logging, config, tests)          │
│                                                                          │
│  8. THE "GOLDEN MODEL" ILLUSION                                         │
│     ─────────────────────────────                                       │
│     Problem: Treating model as sacred, unchangeable                    │
│     Result: Can't improve, can't debug, tribal knowledge              │
│     Solution: Version everything, document decisions, automate         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 13.2 The Right Questions to Ask

Before implementing, ask:

**About the Problem:**
- Can we solve this WITHOUT ML?
- What's the simplest ML approach that might work?
- What does "good enough" look like?

**About the Data:**
- Do we have enough labeled data?
- Where does the data come from?
- How will data quality be maintained?
- What happens when data distribution changes?

**About Operations:**
- How will we monitor this?
- What's our rollback plan?
- Who gets paged if it breaks?
- How do we update the model?

**About the Team:**
- Who will maintain this?
- What skills are needed?
- Is this tech stack sustainable for us?

---

## 14. Checklist for New Projects

Use this checklist when starting a new ML project:

### 14.1 Planning Phase

```markdown
□ Problem Definition
  □ Clear problem statement written down
  □ Success metrics defined (business + technical)
  □ Baseline established (current performance or simple heuristic)
  □ Scope defined (what's in, what's out)

□ Data Assessment
  □ Data sources identified
  □ Data quality evaluated
  □ Labeling strategy defined (if supervised)
  □ Data pipeline requirements understood

□ Architecture Decisions
  □ Inference pattern chosen (real-time, batch, streaming)
  □ Serving strategy chosen (embedded, service, serverless)
  □ Repository structure decided (mono vs poly)
  □ Key technology choices made and documented
```

### 14.2 Development Phase

```markdown
□ Infrastructure Setup
  □ Development environment reproducible (Docker, conda)
  □ Version control for code, data, models
  □ Experiment tracking configured
  □ CI/CD pipeline for code (linting, tests)

□ Data Pipeline
  □ Data ingestion automated
  □ Preprocessing code modular and tested
  □ Feature engineering documented
  □ Data validation in place

□ Model Development
  □ Baseline model working end-to-end
  □ Evaluation metrics implemented
  □ Hyperparameter search configured
  □ Model serialization working
```

### 14.3 Production Phase

```markdown
□ Serving Infrastructure
  □ Model serving endpoint deployed
  □ Load testing performed
  □ Fallback mechanism implemented
  □ Auto-scaling configured

□ Monitoring
  □ System metrics (latency, throughput, errors)
  □ Model metrics (predictions, confidence)
  □ Data metrics (input distribution, drift)
  □ Alerting configured

□ Operations
  □ Deployment process documented
  □ Rollback procedure tested
  □ On-call runbook created
  □ Incident response process defined
```

### 14.4 Continuous Improvement

```markdown
□ Feedback Loop
  □ User feedback collection mechanism
  □ Correction/label collection pipeline
  □ Retraining trigger defined
  □ A/B testing infrastructure ready

□ Documentation
  □ Architecture documented
  □ API documented
  □ Runbooks maintained
  □ Decision records kept
```

---

## Conclusion

The key insights to remember:

1. **Start simple, evolve as needed** - Don't build for Google scale on day one
2. **Separate concerns** - Data, model, serving, and application are different problems
3. **Plan for failure** - Graceful degradation, monitoring, and rollback
4. **Close the loop** - Feedback from production improves your models
5. **Document decisions** - Future you will thank present you

The best architecture is one that:
- Solves today's problems
- Doesn't prevent tomorrow's solutions
- Can be understood by your team
- Can be operated reliably

---

**Remember:** Architecture is not about being right, it's about being adaptable.


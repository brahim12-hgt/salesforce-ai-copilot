# Architecture

```
Commercial ─▶ LWC (Lightning) ─▶ Apex (USER_MODE) ─▶ Named Credential ─▶ FastAPI
                                                                          │
                          ┌───────────────────────────────────────────────┤
                          ▼               ▼                ▼              ▼
                    ML calibré        SHAP (XAI)     LLM + règles     RAG TF-IDF
                          └──────────────┬─────────────────┘
                                         ▼
                             Next Best Action (règles + SHAP)
                                         ▼
                     Retour Salesforce → décision humaine → AI_Recommendation__c + audit_log.jsonl
```

| Module | Fichier |
|---|---|
| 1 Analyse des données | `ml/prepare_maven.py`, `ml/features.py`, `backend/app/services/data_source.py` |
| 2 Scoring prédictif | `ml/train.py`, `backend/app/services/ml_service.py` |
| 3 Explainable AI | `ml_service.predict_one` (SHAP, agrégation one-hot) |
| 4 IA générative | `backend/app/services/llm_service.py` |
| 5 Next Best Action | `backend/app/services/recommender.py` |
| 6 Assistant conversationnel + RAG | `chat_service.py`, `rag_service.py`, LWC `copilotChat` |
| 7 Dashboard | `GET /v1/dashboard`, LWC `copilotDashboard` |

## Sécurité
- Clé API serveur-à-serveur dans le Named Credential (jamais côté navigateur), comparaison à temps constant.
- Apex `with sharing` + `WITH USER_MODE` : l'IA ne reçoit que les données visibles par l'utilisateur.
- Données synthétiques par défaut ; le contenu des interactions est traité comme donnée (prompt LLM protégé).
- Toute recommandation exige une décision humaine (accepter / modifier / rejeter), tracée dans le CRM et dans `data/audit_log.jsonl`.
- Surveillance de dérive : `GET /v1/model/metrics` + journal des décisions ; ré-entraîner avec `make train`.

## Limites connues
- Le dataset Maven est fictif et sans interactions textuelles ; les performances sur un vrai CRM peuvent différer.
- `data_source.py` lit les CSV préparés pour dashboard/chat ; en production, remplacer par `sf_client()` (SOQL).
- Pour une affaire Salesforce, les champs absents sont complétés par `ml_service.enrich` (référentiels Maven si les noms correspondent, sinon médianes).
- Le RAG est un index TF-IDF en mémoire ; pour un volume réel, passer à des embeddings + base vectorielle.

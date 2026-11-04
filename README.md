# Salesforce AI Copilot

Copilote IA pour Salesforce : scoring prédictif des opportunités, explications SHAP, analyse des interactions par LLM, recommandations (Next Best Action), assistant conversationnel et dashboard Lightning.

## 0. Dataset : CRM Sales Opportunities (Maven Analytics / Kaggle)
Dataset B2B fictif (vendeur de matériel informatique) : 4 fichiers CSV, ~8 800 opportunités dans `sales_pipeline.csv`.
1. Téléchargez-le (Kaggle ou mavenanalytics.io/data-playground/crm-sales-opportunities) et vérifiez sa licence.
2. Placez dans `data/raw/` : `sales_pipeline.csv`, `accounts.csv`, `products.csv`, `sales_teams.csv`.
3. `make real` : jointure des tables, calcul des features, entraînement. Le script affiche clairement toute colonne manquante.

Choix de modélisation :
- Cible : `Won` / `Lost` (seules les affaires closes servent à l'entraînement ; les affaires `Prospecting`/`Engaging` sont celles que l'on score).
- **Pas de fuite** : `close_value`, `close_date` et la durée de l'affaire sont exclus (connus seulement après le résultat).
- Taux de succès passés du client et du commercial, calculés **uniquement sur les affaires closes avant l'engagement** et lissés.
- Découpage **chronologique** (70 / 15 / 15 %).
- `GTXPro` / `GTX Pro` (orthographes différentes entre tables) sont rapprochés automatiquement.

Limites de ce dataset (à dire dans votre rapport) :
- Il **ne contient ni e-mails, ni appels, ni réunions** : le module « analyse des interactions » ne peut pas être alimenté par ce dataset. Il fonctionne avec les activités Salesforce (Task) ou des textes que vous fournissez.
- Il est fictif et son signal prédictif est probablement faible : attendez-vous à un AUC modeste. Les métriques réelles sont écrites dans `models/metrics.json`.

Sans les vrais fichiers, `make sample` génère de **fausses** données au même format pour tester le code.

## 1. Démarrage local (backend, sans Salesforce)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # renseigner API_KEY (et ANTHROPIC_API_KEY, optionnel)
make real                       # (ou make sample pour tester sans le dataset)
make test
make run                        # http://localhost:8000/docs
```
Exemple (prenez un `opportunity_id` dans `data/open_opportunities.csv`) :
```bash
curl -X POST localhost:8000/v1/opportunities/<ID>/insights -H "X-API-Key: <API_KEY>"
```

## 2. API
| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | état |
| POST | `/v1/opportunities/{id}/predict` | score + facteurs SHAP |
| POST | `/v1/opportunities/{id}/summary` | résumé / besoins / objections / engagements |
| POST | `/v1/opportunities/{id}/insights` | flux complet (ML → SHAP → LLM → NBA) |
| GET | `/v1/dashboard` | KPI, répartition, top priorités |
| POST | `/v1/chat` | assistant en langage naturel |
| POST | `/v1/decisions` | validation humaine tracée |
| GET | `/v1/model/metrics` | métriques et calibration |

## 3. Déploiement Salesforce
1. Déployer le backend (`docker compose up --build`) sur une URL HTTPS.
2. Dans `namedCredentials/AI_Copilot`, renseigner l'URL ; saisir `API_KEY` comme mot de passe dans Setup → Named Credentials (cocher *Allow Merge Fields in HTTP Header*).
3. `cd salesforce && sf project deploy start --source-dir force-app`
4. Assigner le Permission Set **AI Copilot User**.
5. Lightning App Builder : ajouter `AI Opportunity Insights` à la page d'enregistrement Opportunity ; `AI Copilot Dashboard` et `AI Copilot Assistant` à une App Page.
6. Flow (optionnel) : Record-Triggered Flow sur Opportunity → action *Score Opportunity with AI Copilot* (Apex invocable).
7. Remote Site / CSP : l'appel passe par le Named Credential, rien d'autre à autoriser.

## 4. Structure
```
ml/            features, préparation du dataset Maven, entraînement (LogReg, RF, GB, XGBoost + calibration isotonic)
backend/app/   FastAPI, services (ml/SHAP, llm, rag, recommender, chat), sécurité
backend/tests/ tests d'API
salesforce/    objets & champs, Apex, 3 LWC, Named Credential, Permission Set
docs/          architecture
```

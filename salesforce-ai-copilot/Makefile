install:
	pip install -r requirements.txt
# --- avec le VRAI dataset (4 CSV dans data/raw/) ---
prepare:
	cd ml && python prepare_maven.py --raw ../data/raw
train:
	cd ml && python train.py
real: prepare train
# --- démo avec de FAUSSES données au même format (test du code uniquement) ---
sample:
	cd ml && python make_fixture.py && python prepare_maven.py --raw ../data/raw_sample && python train.py
run:
	uvicorn backend.app.main:app --reload --port 8000
test:
	python -m pytest backend/tests -q
deploy-sf:
	cd salesforce && sf project deploy start --source-dir force-app

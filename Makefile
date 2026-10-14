.PHONY: setup test lint format demo serve ingest eval sweep gate calibrate build-eval-set docker clean

UV ?= uv
PORT ?= 8000

setup:            ## install Python 3.12 toolchain and dependencies
	$(UV) python install 3.12
	$(UV) sync
	@test -f .env || cp .env.example .env

test:             ## run the test suite with the fake provider
	LLM_PROVIDER=fake $(UV) run pytest

lint:             ## ruff lint + format check
	$(UV) run ruff check src tests scripts
	$(UV) run ruff format --check src tests scripts

format:           ## auto-format
	$(UV) run ruff format src tests scripts
	$(UV) run ruff check --fix src tests scripts

ingest:           ## build and persist the chunk index from CORPUS_PATH
	$(UV) run python scripts/ingest.py

demo:             ## ask a few questions from the CLI
	$(UV) run python scripts/demo.py

serve:            ## run the API + UI on http://localhost:$(PORT)
	$(UV) run uvicorn docs_rag.api.app:app --host 0.0.0.0 --port $(PORT)

build-eval-set:   ## regenerate evals/golden/questions.jsonl and the hand-label sample
	$(UV) run python scripts/build_eval_set.py

eval:             ## evaluate naive / hybrid / reranked / final and write reports/
	$(UV) run python scripts/eval.py --mode all

sweep:            ## chunk size / overlap sweep -> reports/chunk_sweep.md
	$(UV) run python scripts/sweep_chunks.py

gate:             ## regression gate against reports/baseline.json
	$(UV) run python scripts/gate.py --baseline reports/baseline.json --candidate reports/eval-latest.json --config evals.yaml

calibrate:        ## judge calibration against evals/human_labels.jsonl
	$(UV) run python scripts/calibrate_judge.py

docker:           ## build the container image
	docker build -t docs-rag:latest .

clean:
	rm -rf .pytest_cache .ruff_cache data/index traces/*.jsonl

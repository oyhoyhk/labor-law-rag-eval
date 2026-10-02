ingest:
	uv run python -m app.ingest.provision
	uv run python -m app.index build --strategy article
	uv run python -m app.index build --strategy fixed
	uv run python -m app.index build --strategy precedent

eval:
	uv run python -m eval.run --name $(or $(NAME),baseline) $(ARGS)

retrieval:
	uv run python -m eval.retrieval_check $(ARGS)

test:
	uv run pytest -q

verify-gold:
	uv run python scripts/verify_gold.py

.PHONY: ingest eval retrieval test verify-gold

calibrate:
	uv run python -m eval.calibrate $(ARGS)

compare:
	uv run python -m eval.compare $(ARGS)

.PHONY: calibrate compare

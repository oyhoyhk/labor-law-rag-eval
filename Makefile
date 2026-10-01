eval:
	uv run python -m eval.run --name $(or $(NAME),baseline) $(ARGS)

retrieval:
	uv run python -m eval.retrieval_check $(ARGS)

test:
	uv run pytest -q

verify-gold:
	uv run python scripts/verify_gold.py

.PHONY: eval retrieval test verify-gold

calibrate:
	uv run python -m eval.calibrate $(ARGS)

compare:
	uv run python -m eval.compare $(ARGS)

.PHONY: calibrate compare

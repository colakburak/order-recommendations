IMAGE ?= order-rec
NAME  ?= order-rec
PORT  ?= 8000
STORE ?= store_a
DATE  ?= 2024-01-01

URL := http://localhost:$(PORT)

.DEFAULT_GOAL := help
.PHONY: help build run stop logs load-data query demo test lint dev

help:  ## Show this help
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

demo: build run load-data query  ## Build, start, load every CSV, then show recommendations

build:  ## Build the Docker image
	docker build -t $(IMAGE) .

run: stop  ## Start the container and wait until it answers
	docker run -d --name $(NAME) -p $(PORT):8000 $(IMAGE)
	@echo "waiting for $(URL) ..."
	@for i in $$(seq 30); do \
		curl -sf $(URL)/docs >/dev/null && echo "ready" && exit 0; \
		sleep 0.5; \
	done; \
	echo "service did not come up"; docker logs $(NAME); exit 1

stop:  ## Stop and remove the container
	@docker rm -f $(NAME) 2>/dev/null || true

logs:  ## Follow the container logs
	docker logs -f $(NAME)

# order_recommendations.csv is served at /load/recommendations -- the one place where the
# file name and the URL segment disagree, so the mapping lives here rather than in a README.
load-data:  ## Load all four CSVs from data/ into the running service
	@for pair in items:items orderable_items:orderable_items \
	             inventory:inventory order_recommendations:recommendations; do \
		file=$${pair%%:*}; endpoint=$${pair##*:}; \
		printf '%-31s ' "data/$$file.csv"; \
		curl -sf -X POST -F "file=@data/$$file.csv" $(URL)/load/$$endpoint | jq -c '.metadata'; \
	done

query:  ## Show recommendations for $(STORE) on $(DATE)
	@curl -sf "$(URL)/stores/$(STORE)/recommendations?date=$(DATE)" \
		| jq '{store_id, date, count, first_two: .recommendations[:2]}'

test:  ## Run the test suite
	uv run pytest -q

lint:  ## Lint with ruff
	uv run ruff check .

dev:  ## Run the API locally with reload, no Docker
	uv run uvicorn app.main:app --reload

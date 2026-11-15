# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

LICENSE := \
	-c "Maestro authors and contributors" -y 2026 \
	--contributor "Cedric Hirschi <cedr02@live.com>" --contributor "Tim Frey <timfreyb@gmail.com>" \
	-l "Apache-2.0" \

format:
	uv run ruff format

format_without_tests:
	uv run ruff format --exclude tests

check:
	uv run ruff check --fix

check_without_tests:
	uv run ruff check --fix --exclude tests

typecheck:
	uv run ty check

typecheck_without_tests:
	uv run ty check --exclude tests

pre-commit:
	uv run prek run --all-files

.PHONY: format format_without_tests check check_without_tests typecheck typecheck_without_tests pre-commit

lint: format check typecheck pre-commit

lint_without_tests: format_without_tests check_without_tests typecheck_without_tests

test:
	uv run pytest

.PHONY: lint lint_without_tests test

license:
	uv run reuse annotate $(LICENSE) \
	--style python \
	src/maestro/assets/containers/*.def

	uv run reuse annotate $(LICENSE) \
	--skip-unrecognised \
	tests/ src/ --recursive

	uv run reuse annotate $(LICENSE) \
	--style python \
	./*.yml ./.*.yaml ./*.toml ./*.yml.example ./Makefile ./.gitignore

	uv run reuse lint

.PHONY: license

docs_build:
	uv run mkdocs build

docs_serve:
	uv run mkdocs serve

.PHONY: docs_build docs_serve

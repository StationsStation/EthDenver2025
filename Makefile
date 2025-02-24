# Makefile

HOOKS_DIR = .git/hooks

.PHONY: clean
clean: clean-build clean-pyc clean-test clean-docs

.PHONY: clean-build
clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr deployments/build/
	rm -fr deployments/Dockerfiles/open_aea/packages
	rm -fr pip-wheel-metadata
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +
	find . -name '*.svn' -exec rm -fr {} +
	find . -name '*.db' -exec rm -fr {} +
	rm -fr .idea .history
	rm -fr venv

.PHONY: clean-docs
clean-docs:
	rm -fr site/

.PHONY: clean-pyc
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test:
	rm -fr .tox/
	rm -f .coverage
	find . -name ".coverage*" -not -name ".coveragerc" -exec rm -fr "{}" \;
	rm -fr coverage.xml
	rm -fr htmlcov/
	rm -fr .hypothesis
	rm -fr .pytest_cache
	rm -fr .mypy_cache/
	find . -name 'log.txt' -exec rm -fr {} +
	find . -name 'log.*.txt' -exec rm -fr {} +

.PHONY: hashes
hashes: clean
	poetry run autonomy packages lock
	poetry run autonomy push-all

lint:
	poetry run adev -v -n 0 lint

fmt: 
	poetry run adev -n 0 fmt

test:
	poetry run adev -v test

install:
	@echo "Setting up Git hooks..."

	# Create symlinks for pre-commit and pre-push hooks
	cp scripts/pre_commit_hook.sh $(HOOKS_DIR)/pre-commit
	cp scripts/pre_push_hook.sh $(HOOKS_DIR)/pre-push
	chmod +x $(HOOKS_DIR)/pre-commit
	chmod +x $(HOOKS_DIR)/pre-push
	@echo "Git hooks have been installed."
	@echo "Installing dependencies..."
	bash install.sh
	@echo "Dependencies installed."
	@echo "Syncing packages..."
	poetry run autonomy packages sync
	@echo "Packages synced."

 sync:
	git pull
	poetry run autonomy packages sync

all: fmt lint test hashes
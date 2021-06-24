.PHONY: default
default:
	false

.PHONY: lint
lint:
	flake8

.PHONY: test
test:
	python -m unittest test.sensors.test_status_test

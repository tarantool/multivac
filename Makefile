.PHONY: default
default:
	false

.PHONY: test
test:
	python -m unittest test.sensors.fails_test

.PHONY: default
default:
	false

.PHONY: test
test:
	python -m unittest test.sensors.test_status_test

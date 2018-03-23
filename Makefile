all: test

test:
	@pytest tests

.PHONY: all test

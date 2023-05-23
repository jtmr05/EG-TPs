.DEFAULT_GOAL := clean

.PHONY: clean
clean:
	-rm -rf .coverage __pycache__ out/ *.log

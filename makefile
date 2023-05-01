.DEFAULT_GOAL := clean

.PHONY: clean
clean:
	-rm -f *.html *.log .coverage
	-rm -rf __pycache__

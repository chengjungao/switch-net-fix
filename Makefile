PY ?= python
PORT ?= 8080

.PHONY: help test run check build clean

help:
	@echo "make test    运行全部测试"
	@echo "make run     启动服务（PORT=$(PORT)）"
	@echo "make check   编译检查"
	@echo "make build   构建 wheel"

test:
	$(PY) -m unittest discover -s tests -t . -v

run:
	$(PY) -m switch_net_fix --port $(PORT)

check:
	$(PY) -m compileall -q switch_net_fix tests

build:
	$(PY) -m pip wheel --no-deps -w dist .

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf logs

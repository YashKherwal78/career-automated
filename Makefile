.PHONY: dev attach stop restart

dev:
	@bash scripts/dev.sh

attach:
	@bash scripts/attach.sh

stop:
	@bash scripts/stop.sh

restart:
	@bash scripts/restart.sh

# This makefile provides some convenient commands for setting up a local Elogy instance
# for development or testing. It does not install anything globally.

install:
	cd backend && $(MAKE) install
	cd frontend && $(MAKE) install

run-backend:
	cd backend && $(MAKE) run

run-frontend:
	cd frontend && $(MAKE) run

# Run this command with "make run -j2", that way backend and frontend run simultaneously
run: run-backend run-frontend

# Only runs backend tests (currently there are no frontend tests anyway)
test:
	cd backend && $(MAKE) test

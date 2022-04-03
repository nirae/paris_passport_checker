.PHONY: all build up upd restart down

all: up

freeze:
	pipenv run pip3 freeze > requirements.txt

build:
	docker build -t slot_checker .

up:
	docker-compose up --build

upd:
	docker-compose up --build -d

restart:
	docker-compose restart

down:
	docker-compose down

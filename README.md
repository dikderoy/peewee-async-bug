# how to run the test

things required:
    - MySQL DB daemon accessible to script

you may use docker (docker-compose file provided)
 or run and configure maria/mysql db installation yourself

## install requirements

    pip install -r requirements

## run test:

### using docker and docker-compose

- docker >= 1.12
- docker-compose >= 1.8
- python >= 3.5

1. run `docker-compose up -d` in the root of a repo
2. run `python app/test_item_save_handler.py`

### using self configured mysql/maria installation

1. run db host
2. run `db_bootstrap.sql` using tool of your choice to create db and user
3. alter connection settings in `app/settings.py` if necessary
4. run `python app/test_item_save_handler.py`
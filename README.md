

# Docker environment configuration

## Setup a container with DB server:
```
docker run --name db -e MYSQL_ROOT_PASSWORD=test -d -p 3306:3306 mariadb
# -e -- environment
# -d -- run as a daemon
# -p -- map ports
```

## Run client to test connection to DB:
```
docker run --name mysql-client -it --link db:mysql --rm mariadb sh -c 'exec mysql -uroot -ptest -hmysql'
# -it -- interactive
# --rm -- remove after exiting 
```

## Create image for the app:
```
docker build -t flask_blog .
## -t -- tag
```
## Run a container with the new image:

```
docker run -id -p 5000:5000 -v $HOME/flask_blog:/opt/flask_blog --name blog --link db:mysql flask_blog bash
# -id -- interactive and daemon
# -v -- mount a volume 
```

### To access docker, create tables, and start the app:

```
docker exec -it blog bash 
# -it -- interactive terminal

./manage.py shell
from flask_blog inport db
db.create_all()
^D
./manage.py runserver
```

### To find out the IP of the container run:

```
docker inspect blog
#172.17.0.4
```

# How to Deploy Changes to App

Follow these steps to deploy changes to the app. Assumes the server and app have already been [deployed](https://github.com/codyschank/application/blob/master/deploy.md), and that the app updates have been merged to the master branch.


### Pull the latest version

`cd` into the repository and pull the latest: `$ git pull`


### Restart the app.

First, verify if the app container is running:
```
$ sudo docker ps

# If the container is running it will be listed here
CONTAINER ID        IMAGE                  COMMAND                  CREATED             STATUS              PORTS                    NAMES
dd62ece05cc5        claryjohn/mapthevote   "bash -c 'flask run …"   5 days ago          Up 5 days        0.0.0.0:5000->5000/tcp   mapthevote
```

If the container is running, restart it with `$ sudo docker restart mapthevote`

If the container is missing or not running, run the app in a new container:

```bash
$ sudo docker run \
    --name mapthevote \
    -p 5000:5000 \
    -d \
    --rm \
    -v /home/ubuntu/application:/app claryjohn/mapthevote \
    bash -c "flask run --host=0.0.0.0 --port=5000"

# veryify the container is running
$ sudo docker ps

CONTAINER ID        IMAGE                  COMMAND                  CREATED             STATUS              PORTS                    NAMES
dd62ece05cc5        claryjohn/mapthevote   "bash -c 'flask run …"   3 seconds ago       Up 2 seconds        0.0.0.0:5000->5000/tcp   mapthevote
```

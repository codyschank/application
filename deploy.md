# How to Deploy Map the Vote

### Create Instance and Configure Network

Create an EC2 instance running Ubuntu 16. Make sure instance is on a VPC with public access allowed over port 80. Use AWS Route 53 to update A record to point to instance IP address.

Connect to instance over SSH and follow steps below.

### Clone repo

Ubuntu comes with git pre-installed. So you just need to clone the repo.

```bash
$ git clone https://github.com/codyschank/application
```

### Add secrets.py
Create `secrets.py` and add it to `/mapthevote` directory. This file contains keys for connecting to the address database. Contact the project admins for access to the address database.

The file should contain a single `AUTH` dictionary structured like so:

```python
AUTH = {
    'pass':'your-secret-password',
    'user':'your-secret-username',
    'endpoint':'your-database-endpoint',
    'dbname':'your-database-name',
    'flask_secret':'your-flask-secret-key',
    'googlemaps_key':'your-google-maps-key-1',
    'googlemaps_key2':'your-google-maps-key-2'
}
```

### Install Docker
We use docker to manage the python environment.  See Docker's [docs](https://docs.docker.com/install/linux/docker-ce/ubuntu/#set-up-the-repository).

```bash
$ sudo apt-get update

$ sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common

$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

$ sudo apt-key fingerprint 0EBFCD88

$ sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

$ sudo apt-get update

$ sudo apt-get install docker-ce

#  docker should start automatically, but you can start it with
$ sudo systemctl start docker
```

### Pull the Docker image

```bash
$ sudo docker pull claryjohn/mapthevote
```

### Install nginx

We use nginx as a reverse proxy server to our flask app.

```bash
# install
$ sudo apt-get install nginx

# update firewall rules
$ sudo ufw allow 'Nginx HTTP'

# enter the repo directory
$ cd /home/ubuntu/application

# copy app config from repo to nginx
# the config routes HTTP traffic to localhost port 5000 (our flask app)
$ sudo cp app.conf /etc/nginx/sites-available/

# restart nginx
$ service nginx restart
```

### Run the app

This command mounts the repo into the container and binds the host port 5000 to the container.

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

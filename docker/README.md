## Prepare environment file

Sample environment file is "sample.env". Rename it, add secret values and source it before executing any docker commands

```bash
source staging.env
```


## Build base images
Build base images used by Docker Compose. 
These images should be rebuilt only if list of packages in requitements.txt changes

```bash
./build-docker-base.sh
```

## Build container images
Build container images used by Docker Compose. 
These images should be every time code changes.

```bash
./build-docker-images.sh
```


## Start system

```bash
cd docker
docker-compose up
```
Look for other docker-compose commands at https://docs.docker.com/compose/reference/overview/


## Destroy system
This command deletes all volumes, database and cached containers
```bash
cd docker
docker-compose down
```


## Notes

SSL cetificates will be generated by Let's Encrypt with "--staging" option. 
It produces untrusted certificates. If you want to produce valid SSL certificates
remove --staging option from certbot commands in nginx-entrypoint-swarm.sh

For local only deployment that does not use HTTP 
set DEPLOYMENT_TYPE=local in the environment file, see sample.env
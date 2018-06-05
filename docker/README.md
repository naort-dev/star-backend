## Build base images
Build base images used by Docker Compose

```bash
./build-images.sh
```


## Prepare environment file

Sample environment file is "sample.env". Rename it, add secret values and source it before executing any docker commands

```bash
source staging.env
```

## Build images

```bash
docker-compose build
```

## Start system

```bash
docker-compose up
```
Look for other docker-compose commands at https://docs.docker.com/compose/reference/overview/


## One time load data

```bash
docker-compose -f loaddatas.yml up
```


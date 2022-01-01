# Motivation
I don't think I'm telling you anything new when I say that the dependencies between different python lib's/frameworks used in a data pipeline and running on a cluster can be hell. 
The idea of this repo was to create an example that shows the containerization of these tasks orchestrated by [Apache Airflow](https://airflow.apache.org).

## How to setup
The example requires [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

## Running Components
All components are composed in one _docker-composer_ file and runnable with `docker-compose -f docker-compose.yaml up -d`, if you have Docker and Docker Compose installed.

# Modifications:
## docker-compose modifications to add _Connections_
There are several options to deploy _Connections_ automatically here via docker-dompose file. 
The connection can also be entered manually via Airflow > Admin > Connection UI beforehand and exported afterwards.

```
environment:
    &airflow-common-env
    AIRFLOW_CONN_FS_CONN: fs://airflow:airflow@?path=%2Ftmp%2Fdata%2F # will NOT show up in Admin > Connection UI
```

## docker-compose modifications to add a proxy between Docker and Airflow DockerOperator
Besides, the standard _docker-compose_ file (current version 2.2.3) you need to add a proxy (socat lib.) to invoke via `docker.sock` the containerized tasks from the Airflow DockerOperator. 
I have added _socat_ [socat - getting started](https://www.redhat.com/sysadmin/getting-started-socat) in an additional container to the end of the _docker-compose_ file.

```
  docker-proxy:
    container_name: docker-proxy
    image: brainiac/socat:0.1.0
    command: "TCP4-LISTEN:2375,fork,reuseaddr UNIX-CONNECT:/var/run/docker.sock"
    restart: always
    ports:
      - "2376:2375"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```


## Usage of Airflow DockerOperator

Within the Airflow DAG the `docker_url='tcp://docker-proxy:2375'` can now be used in the DockerOperator, the before added proxy to the necessary re-routing

```
task2 = DockerOperator(
            task_id='docker_command_' + str(i),
            image='brainiac/multiarch-python-3.11-example:0.1.1',
            command='',
            api_version='auto',
            auto_remove=True,
            docker_url='tcp://docker-proxy:2375',
            network_mode="bridge"
        )
```


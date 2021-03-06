# Motivation
I don't think I'm telling you anything new when I say that the dependencies between different python lib's/frameworks used in a data pipeline and running on a cluster can be hell. 
The idea of this repo was to create an example that shows the containerization of these tasks orchestrated by [Apache Airflow](https://airflow.apache.org).

## How to setup
The example requires [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

For data sharing you need a (tmp) dir. e.g.
```bash
mkdir /tmp/data
```

### Running Components
All components are composed in one _docker-composer_ file and runnable with `docker-compose -f docker-compose.yaml up -d`, if you have Docker and Docker Compose installed.

```bash
docker-compose -f docker-compose.yaml up -d
```

### login into Airflow
```bash
username: airflow
password: airflow
```
[http://localhost:8080](http://localhost:8080)

### docker-compose modifications to add _Connections_
There are several options to deploy _Connections_ automatically here via docker-dompose file. 
The connection can also be entered manually via Airflow > Admin > Connection UI beforehand and exported afterwards.

#### export existing Airflow Connections

Use `airflow connections list` to get all defined _Connections_. Use get_uri as _environment variable_

```bash
id | conn_id | conn_type | description | host | schema | login   | password | port | is_encrypted | is_extra_encrypted | extra_dejson           | get_uri
===+=========+===========+=============+======+========+=========+==========+======+==============+====================+========================+============================================
1  | fs_comm | fs        |             |      |        | airflow | airflow  | None | False        | False              | {'path': '/tmp/data/'} | fs://airflow:airflow@?path=%2Ftmp%2Fdata%2F

```

#### add connections to _docker-composer_ file
```
environment:
    &airflow-common-env
    AIRFLOW_CONN_FS_CONN: fs://airflow:airflow@?path=%2Ftmp%2Fdata%2F # will NOT show up in Admin > Connection UI
```

# Adjustements for docker-in-docker
## docker-compose modifications to add a proxy between Docker and Airflow DockerOperator
Besides, the standard _docker-compose_ file (current version 2.2.3) you need to add a proxy (socat lib.) to invoke via `docker.sock` the containerized tasks from the Airflow DockerOperator. 
I have added _socat_ [socat - getting started](https://www.redhat.com/sysadmin/getting-started-socat) in an additional container to the end of the _docker-compose_ file.

```yaml
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

Within the Airflow DAG the `docker_url='tcp://docker-proxy:2375'` can now be used in the DockerOperator, the before added proxy to the necessary re-routing.

data can be shared with mount points. For more details see [Manage data in docker](https://docs.docker.com/storage)

```yaml
task2 = DockerOperator(
            task_id='docker_command_' + str(i),
            image='brainiac/multiarch-python-3.11-example:0.1.1',
            command='',
            api_version='auto',
            auto_remove=True,
            docker_url='tcp://docker-proxy:2375',
            network_mode="bridge",
            mount_tmp_dir=False,
            mounts=[
                Mount(source="/tmp/data", target="/tmp/data", type="bind"),
                ]
        )
```


# Add TIG Monitoring Stack (Telegraf, IndluxDB, Grafana) to _docker-compose_ file


```bash

????????? grafana
???   ????????? dashboards               #  pre-loaded dashboards 
???   ???   ????????? Example Folder
???   ???   ???   ????????? example_dashboard.json
???   ???   ????????? demo-1641121083158.json
???   ????????? grafana.ini
???   ????????? plugins
???   ????????? provisioning
???       ????????? dashboards
???       ???   ????????? dashboard.yml    #  pre-config dashboard settings
???       ????????? datasources
???           ????????? InfluxDB.yml     #  pre-config data source for Grafana (as default)
????????? telegraf
    ????????? telegraf.conf               # config Statsd UDP/TC Server as input [inputs.statsd] and InfluxDB as output [outputs.InfluxDB] 
```

enhanced _docker-compose_ file
```yaml
  telegraf:
    container_name: telegraf
    image: telegraf:1.21.1
    restart: always
    depends_on: 
      - influxdb
    volumes:
      - ./config/telegraf/telegraf.conf:/etc/telegraf/telegraf.conf:ro
  
  influxdb:
    container_name: influxdb
    image: influxdb:1.8.10
    ports: 
      - "8083:8083"
      - "8086:8086"
    restart: always
    environment:
      - INFLUXDB_DB=telegraf
      - INFLUXDB_ADMIN_USER=telegraf
      - INFLUXDB_ADMIN_PASSWORD=supersecret1
      - INFLUXDB_HTTP_AUTH_ENABLED=false

  grafana:
    container_name: grafana-dashboards
    image: grafana/grafana
    restart: always
    ports: 
      - "3000:3000"
    depends_on: 
      - influxdb
    volumes:
      - ./config/grafana/grafana.ini:/etc/grafana/grafana.ini
      - ./config/grafana/provisioning/datasources/:/etc/grafana/provisioning/datasources/
      - ./config/grafana/provisioning/dashboards/:/etc/grafana/provisioning/dashboards/
      - ./config/grafana/dashboards/:/var/lib/grafana/dashboards/
      - ./config/grafana/plugins/:/var/lib/grafana/plugins/
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
      - GF_AUTH_DISABLE_LOGIN_FORM=true
```

## Run TIG stack
... start and init will take a few minutes! Good opportunity to get a coffee 

```bash
docker-compose -f docker-compose-TIG.yaml up -d
```

# Add SPG Monitoring Stack (statsd-exporter, Prometheus, Grafana) to _docker-compose_ file

If you pref. Prometheus which pulls the data from statsd-exporter
```bash
docker-compose -f docker-compose-SPG.yaml up -d
```

enhanced _docker-compose_ file. 
```yaml
  statsd-exporter:
    container_name: airflow-statsd-exporter
    image: prom/statsd-exporter:v0.22.4
    command: "--statsd.listen-udp=:8125 --web.listen-address=:9102 --statsd.mapping-config=/tmp/statsd_mapping.yml"
    ports:
      - 9102:9102
      - 8125:8125/udp
    volumes:
            - ./config/statsd//statsd_mapping.yml:/tmp/statsd_mapping.yml

  prometheus:
    container_name: airflow-prometheus
    image: prom/prometheus
    ports:
        - 9090:9090
    depends_on: 
      - statsd-exporter
    volumes:
        - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    container_name: grafana-dashboards
    image: grafana/grafana
    restart: always
    ports: 
      - "3000:3000"
    depends_on: 
      - prometheus
    volumes:
      - ./config/grafana/grafana.ini:/etc/grafana/grafana.ini
      - ./config/grafana/provisioning/datasources/:/etc/grafana/provisioning/datasources/
      - ./config/grafana/provisioning/dashboards/:/etc/grafana/provisioning/dashboards/
      - ./config/grafana/dashboards/:/var/lib/grafana/dashboards/
      - ./config/grafana/plugins/:/var/lib/grafana/plugins/
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
      - GF_AUTH_DISABLE_LOGIN_FORM=true
```

# DAG templating multi-file
with `dag-templating/`:
 - `dag-config/` contains two Json configuration files with parameters used to dynamically generate Python files for `dag_file_1.py` and `dag_file_2.py`.
 - `dag-template.py` contains the starting DAG template from which other DAG files are dynamically generated.
 - `generate-dag-files.py` contains a script to dynamically generate a DAG file for each config file in `dag-config/` by making a copy of `dag-template.py` and replacing key parameters from the config file.


```yaml
dag-templating
|-- dag-config
|   |-- dag1-config.json
|   `-- dag2-config.json
|-- dag-template.py
`-- generate-dag-files.py


dags
|-- __pycache__
|   |-- dag_file_1.cpython-37.pyc
|   `-- dag_file_2.cpython-37.pyc
|-- dag_file_1.py
|-- dag_file_2.py
```

run generator from the project-root folder _(cached DAGs will clean up during the generation)_
```yaml
python3 dag-templating/generate-dag-files.py
```

# Monitoring
Link to [Grafana Dashboard](http://localhost:3000/d/v6SZeoAnk/demo?orgId=1&refresh=5s)




# result
when everything is started it should look like this:
![This is the result](https://github.com/zBrainiac/docker-airflow/blob/b2595120a0e59ed3ed667611c7de4beb49047939/images/airflow_DockerOperator.mov)


# stop and clean-up
Don't forget to stop and clean-up your environment

```bash
docker-compose down &&
docker rm -f $(docker ps -a -q) &&
docker volume rm $(docker volume ls -q)
```
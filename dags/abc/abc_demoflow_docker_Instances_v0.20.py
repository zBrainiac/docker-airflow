from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.docker_operator import DockerOperator
from airflow.sensors.filesystem import FileSensor
from docker.types import Mount



def _failure_callback(context):
    if isinstance(context['exception'], AirflowSensorTimeout):
        print(context)
        print("Sensor timed out")

with DAG(
    dag_id='abc_demoflow_docker_Instances_v0-2-0',
    schedule_interval='@daily',
    start_date=datetime(2021, 12, 31),
    catchup=True,
    dagrun_timeout=timedelta(minutes=60),
    tags=['MFT', 'raw-data', 'abc'],
    params={"example_key": "example_value"},
) as dag:
    run_this_last = DummyOperator(
        task_id='run_this_last',
    )

    # [START howto_operator_bash]
    run_this = BashOperator(
        task_id='run_after_loop',
        bash_command='echo 1',
    )
    # [END howto_operator_bash]

    run_this >> run_this_last

    for i in range(3):
        task = BashOperator(
            task_id='runme_' + str(i),
            bash_command='echo "{{ task_instance_key_str }}" && sleep 1',
        )
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

        task >> task2 >> run_this

    get_partner_file = FileSensor(
        task_id='get_partner_file',
        poke_interval=60,
        timeout=60 * 30,
        mode="reschedule",
        on_failure_callback=_failure_callback,
        filepath="2021-12-23/partner_b.txt",
        fs_conn_id='fs_conn'
    )

    get_partner_file >> run_this

if __name__ == "__main__":
    dag.cli()

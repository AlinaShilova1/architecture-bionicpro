from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


# ---- Функции-обработчики. Здесь пока только "заглушки" ----

def _extract_from_crm(**context):
    # Здесь в реальности можно использовать PostgresHook и т.п.
    print("[ETL] Extract CRM data (placeholder)")
    # Пример (НЕ обязательно запускать в твоём окружении):
    # from airflow.providers.postgres.hooks.postgres import PostgresHook
    # pg = PostgresHook(postgres_conn_id="postgres_crm")
    # rows = pg.get_records("SELECT ...")
    # context['ti'].xcom_push(key="crm_rows", value=rows)


def _extract_telemetry(**context):
    print("[ETL] Extract telemetry data (placeholder)")
    # Здесь мог бы быть запрос в ClickHouse / сырое хранилище


def _build_report_mart(**context):
    print("[ETL] Build/refresh report mart (placeholder)")
    # Здесь мог бы быть merge в витрину ClickHouse


# ---- Описание DAG ----

default_args = {
    "owner": "data-engineer",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bionicpro_reports_daily",
    description="Daily ETL: CRM + telemetry -> report mart",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 2 * * *",  # каждый день в 02:00
    catchup=False,
    tags=["bionicpro", "reports", "etl"],
) as dag:

    extract_crm = PythonOperator(
        task_id="extract_from_crm",
        python_callable=_extract_from_crm,
        provide_context=True,
    )

    extract_telemetry = PythonOperator(
        task_id="extract_telemetry",
        python_callable=_extract_telemetry,
        provide_context=True,
    )

    build_report_mart = PythonOperator(
        task_id="build_report_mart",
        python_callable=_build_report_mart,
        provide_context=True,
    )

    # Порядок выполнения:
    # сначала вытаскиваем данные из CRM и телеметрии, потом строим витрину
    [extract_crm, extract_telemetry] >> build_report_mart

> Зайка:
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client as ClickHouseClient


CLICKHOUSE_CONN = {
    "host": "clickhouse",   # имя сервиса в docker-compose
    "port": 9000,
    "user": "default",
    "password": "",
    "database": "bionicpro_reports",
}


def _init_clickhouse():
    ch = ClickHouseClient(**CLICKHOUSE_CONN)
    ch.execute("CREATE DATABASE IF NOT EXISTS bionicpro_reports")


def _load_crm_dimension(**context):
    pg_hook = PostgresHook(postgres_conn_id="postgres_crm")
    ch = ClickHouseClient(**CLICKHOUSE_CONN)

    crm_sql = """
        SELECT
            u.id          AS user_id,
            u.country_code,
            p.id          AS prosthesis_id,
            p.device_model,
            p.firmware_version
        FROM crm_users u
        JOIN crm_prostheses p ON p.user_id = u.id;
    """
    rows = pg_hook.get_records(crm_sql)

    ch.execute("""
        CREATE TABLE IF NOT EXISTS dim_user_prosthesis
        (
            user_id          UInt64,
            country_code     FixedString(2),
            prosthesis_id    UInt64,
            device_model     String,
            firmware_version String
        )
        ENGINE = MergeTree
        ORDER BY (user_id, prosthesis_id);
    """)

    ch.execute("TRUNCATE TABLE dim_user_prosthesis;")
    if rows:
        ch.execute("INSERT INTO dim_user_prosthesis VALUES", rows)


def _build_daily_stats(**context):
    ch = ClickHouseClient(**CLICKHOUSE_CONN)
    target_date = (datetime.utcnow() - timedelta(days=1)).date()

    ch.execute("""
        CREATE TABLE IF NOT EXISTS report_prosthesis_daily_stats
        (
            event_date          Date,
            user_id             UInt64,
            prosthesis_id       UInt64,
            country_code        FixedString(2),
            device_model        String,
            firmware_version    String,

            sessions_count      UInt32,
            avg_reaction_ms     Float32,
            p95_reaction_ms     Float32,
            max_reaction_ms     UInt32,

            battery_avg_level   Float32,
            battery_min_level   UInt8,

            errors_count        UInt32,
            overheating_count   UInt32,
            low_battery_count   UInt32,

            last_event_ts       DateTime,
            load_datetime       DateTime DEFAULT now()
        )
        ENGINE = MergeTree
        PARTITION BY toYYYYMM(event_date)
        ORDER BY (user_id, prosthesis_id, event_date);
    """)

    ch.execute(
        "ALTER TABLE report_prosthesis_daily_stats "
        "DELETE WHERE event_date = %(event_date)s",
        {"event_date": target_date}
    )

    insert_sql = """
        INSERT INTO report_prosthesis_daily_stats
        SELECT
            toDate(t.event_ts)                      AS event_date,
            d.user_id                               AS user_id,
            d.prosthesis_id                         AS prosthesis_id,
            d.country_code                          AS country_code,
            d.device_model                          AS device_model,
            d.firmware_version                      AS firmware_version,

            uniqExact(t.session_id)                 AS sessions_count,
            avg(t.reaction_ms)                      AS avg_reaction_ms,
            quantile(0.95)(t.reaction_ms)           AS p95_reaction_ms,
            max(t.reaction_ms)                      AS max_reaction_ms,

            avg(t.battery_level)                    AS battery_avg_level,
            min(t.battery_level)                    AS battery_min_level,

            countIf(t.event_type = 'ERROR')         AS errors_count,
            countIf(t.event_type = 'OVERHEAT')      AS overheating_count,
            countIf(t.event_type = 'LOW_BATTERY')   AS low_battery_count,

            max(t.event_ts)                         AS last_event_ts,
            now()                                   AS load_datetime
        FROM telemetry_raw t
        INNER JOIN dim_user_prosthesis d
            ON d.prosthesis_id = t.prosthesis_id
        WHERE toDate(t.event_ts) = %(event_date)s
        GROUP BY
            event_date,
            user_id,
            prosthesis_id,
            country_code,
            device_model,
            firmware_version
    """

    ch.execute(insert_sql, {"event_date": target_date})


default_args = {
    "owner": "data-engineer",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bionicpro_reports_daily",
    default_args=default_args,
    schedule_interval="0 2 * * *",  # ежедневно в 02:00
    catchup=False,
    max_active_runs=1,
    tags=["bionicpro", "reports", "etl"],
) as dag:

    init_clickhouse = PythonOperator(
        task_id="init_clickhouse",
        python_callable=_init_clickhouse,
    )

    load_crm_dimension = PythonOperator(
        task_id="load_crm_dimension",
        python_callable=_load_crm_dimension,
        provide_context=True,
    )

    build_daily_stats = PythonOperator(
        task_id="build_daily_stats",
        python_callable=_build_daily_stats,
        provide_context=True,
    )

    init_clickhouse >> load_crm_dimension >> build_daily_stats

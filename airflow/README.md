# Apache Airflow

Este diretório contém toda a configuração do Apache Airflow utilizada pela Modern Data Platform.

## Estrutura

```text
airflow/
├── dags/
├── plugins/
├── include/
├── config/
├── logs/
├── tests/
└── utils/
```

## Executar

```bash
docker compose up -d
```

## Listar DAGs

```bash
docker exec -it mdp-airflow-apiserver airflow dags list
```
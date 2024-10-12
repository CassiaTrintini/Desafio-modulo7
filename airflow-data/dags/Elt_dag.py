from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sqlite3
import csv
import base64
from airflow.models import Variable

# Configurações padrão do DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Função para exportar a tabela "Order" para CSV
def extract_orders():
    conn = sqlite3.connect('data/Northwind_small.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM 'Order'")
    orders = cursor.fetchall()

    with open('airflow-data/dags/output_orders.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([i[0] for i in cursor.description])  # Colunas
        writer.writerows(orders)

    conn.close()

#Junção de tabelas  
def process_orders():
    conn = sqlite3.connect('data/Northwind_small.sqlite')
    cursor = conn.cursor()

    query = """
    SELECT SUM(OrderDetail.Quantity) FROM OrderDetail
    JOIN 'Order' ON OrderDetail.OrderID = 'Order'.ID
    WHERE 'Order'.ShipCity = 'Rio de Janeiro';
    """
    cursor.execute(query)
    result = cursor.fetchone()

    with open('airflow-data/dags/count.txt', 'w') as f:
        f.write(str(result[0]))

    conn.close()

 #Função que gera o arquivo txt final com conexão com email
def export_final_answer():
    # Importar o resultado da contagem
    with open('airflow-data/dags/count.txt') as f:
        count = f.read().strip()

    # Obter o email da variável do Airflow
    my_email = Variable.get("my_email")
    message = my_email + count
    message_bytes = message.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')

    # Escrever o arquivo final_output.txt
    with open('airflow-data/dags/final_output.txt', 'w') as f:
        f.write(base64_message)

# DAG
with DAG(
    'elt_dag',
    default_args=default_args,
    description='ETL DAG for Northwind',
    schedule=timedelta(days=1),
    start_date=datetime(2021, 1, 1),
    catchup=False,
) as dag:

    # Task para exportar a tabela 'Order' para CSV
    task_extract_orders = PythonOperator(
        task_id='extract_orders',
        python_callable=extract_orders,
    )

    # Task para calcular a soma de 'Quantity' para o Rio de Janeiro
    task_process_orders = PythonOperator(
        task_id='process_orders',
        python_callable=process_orders,
    )

    # Task final para exportar o resultado final (codificação base64)
    task_export_final_output = PythonOperator(
        task_id='export_final_output',
        python_callable=export_final_answer,
    )

    # Definição da ordem das tasks
    task_extract_orders >> task_process_orders >> task_export_final_output

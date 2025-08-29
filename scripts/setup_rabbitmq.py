"""
Configuração inicial da topologia RabbitMQ para arquitetura orientada a eventos do Jarvis Mark II.
Este script pode ser executado uma vez para garantir que exchanges e filas estejam criadas corretamente.
"""
import pika

RABBITMQ_HOST = 'localhost'  # Ajuste conforme necessário
EXCHANGE = 'jarvis_events'

QUEUES = [
    ('stt_jobs_queue', 'stt.requested'),
    ('tts_jobs_queue', 'tts.requested'),
    ('orchestrator_events_queue', 'stt.completed'),
    ('orchestrator_events_queue', 'stt.failed'),
    ('orchestrator_events_queue', 'tts.completed'),
    ('orchestrator_events_queue', 'tts.failed'),
]

def setup_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type='topic', durable=True)
    # Cria filas e bindings
    for queue, routing_key in QUEUES:
        channel.queue_declare(queue=queue, durable=True)
        channel.queue_bind(exchange=EXCHANGE, queue=queue, routing_key=routing_key)
    print('Exchanges e filas configuradas com sucesso.')
    connection.close()

if __name__ == '__main__':
    setup_rabbitmq()

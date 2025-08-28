import pika
import os
import uuid
import time # Adicionar este import
from loguru import logger # Adicionar este import

class MQClient:
    def __init__(self):
        self.url = os.getenv("RABBITMQ_URL")
        self.connection = pika.BlockingConnection(pika.URLParameters(self.url))
        self.channel = self.connection.channel()
        self.rpc_response = None
        self.rpc_corr_id = None
        
        # For RPC calls, we need a dedicated callback queue
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self._on_rpc_response,
            auto_ack=True
        )

    def _on_rpc_response(self, ch, method, props, body):
        if self.rpc_corr_id == props.correlation_id:
            self.rpc_response = body

    def call(self, queue_name, body, timeout=60):
        """Performs a robust RPC call with an explicit timeout."""
        self.rpc_response = None
        self.rpc_corr_id = str(uuid.uuid4())

        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.rpc_corr_id,
                delivery_mode=2 # Persistent
            ),
            body=body
        )
        
        # --- SUBSTITUA A LÓGICA DE ESPERA BLOQUEANTE PELA LÓGICA ROBUSTA ABAIXO ---
        start_time = time.time()
        logger.debug(f"Aguardando resposta RPC da fila '{queue_name}'...")
        while self.rpc_response is None:
            # Processa eventos de rede por um curto período para não bloquear tudo
            self.connection.process_data_events(time_limit=1)
            
            # Verifica se o timeout foi atingido
            if time.time() - start_time > timeout:
                logger.error(f"RPC call para a fila '{queue_name}' expirou após {timeout} segundos.")
                return None # Retorna None explicitamente em caso de timeout
        
        logger.debug(f"Resposta RPC recebida da fila '{queue_name}'.")
        return self.rpc_response
        # --- FIM DA MUDANÇA ---

    def declare_queue(self, queue_name):
        self.channel.queue_declare(queue=queue_name, durable=True)

    def publish(self, queue_name, body):
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2)
        )

    def start_worker(self, queue_name, callback):
        """Starts a worker to consume messages from a queue."""
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue_name, on_message_callback=callback)
        
        print(f"[*] Worker started for queue '{queue_name}'. To exit press CTRL+C")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print("Worker stopped.")
        finally:
            self.close()

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()

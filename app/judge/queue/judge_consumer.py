import pika
import json
from app.judge.core.judge_core import judge_submission
import os

# 환경 변수에서 로드
RABBITMQ_HOST = os.getenv("JUDGE_QUEUE_DOMAIN_NAME", "rabbitmq")
RABBITMQ_USERNAME = os.getenv("JUDGE_QUEUE_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("JUDGE_QUEUE_PASSWORD", "guest")

REQUEST_QUEUE = os.getenv("JUDGE_QUEUE_REQUEST_QUEUE", "submission_request_queue")
RESULT_QUEUE = os.getenv("JUDGE_QUEUE_RESULT_QUEUE", "submission_result_queue")

def callback(ch, method, properties, body):
    print("[x] 요청 수신:", body)
    try:
        request = json.loads(body)

        response = judge_submission(request)

        ch.basic_publish(
            exchange="",
            routing_key=RESULT_QUEUE,
            body=json.dumps(response),
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("[√] 채점 완료 및 결과 전송")

    except Exception as e:
        print("[!] 채점 중 예외 발생:", str(e))
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consumer():
    print("[*] 채점 요청 큐 소비자 시작")

    credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)

    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue=REQUEST_QUEUE, durable=True)
    channel.queue_declare(queue=RESULT_QUEUE, durable=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=REQUEST_QUEUE, on_message_callback=callback)

    channel.start_consuming()

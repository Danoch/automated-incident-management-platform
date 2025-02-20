import json
import boto3
import os
import logging
import time

# Inicializar clientes AWS
ec2_client = boto3.client("ec2")
sns_client = boto3.client("sns")

# Obtener el ARN del SNS desde variables de entorno
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")

# Configurar logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"🚀 Lambda triggered with event: {json.dumps(event)}")

    detail = event.get("detail", {})
    instance_id = detail.get("instanceId")

    if not instance_id:
        message = "⚠ Incident detected, but no instance information found."
        logger.warning(message)
        send_sns_notification(message)
        return {"statusCode": 400, "body": json.dumps({"message": message})}

    try:
        # Detener la instancia
        logger.info(f"🛑 Stopping instance {instance_id}...")
        ec2_client.stop_instances(InstanceIds=[instance_id])

        # Esperar hasta que la instancia esté completamente detenida
        logger.info(f"⏳ Waiting for instance {instance_id} to stop...")
        waiter = ec2_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=[instance_id])

        # Iniciar la instancia nuevamente
        logger.info(f"🔄 Starting instance {instance_id}...")
        ec2_client.start_instances(InstanceIds=[instance_id])

        message = f"🔴 High CPU usage detected! Restarted EC2 instance: {instance_id}"
        logger.info(f"✅ Instance {instance_id} successfully restarted.")

    except Exception as e:
        message = f"❌ Failed to restart EC2 instance {instance_id}: {str(e)}"
        logger.error(message)

    # Enviar notificación por SNS
    send_sns_notification(message)

    return {"statusCode": 200, "body": json.dumps({"message": message})}

def send_sns_notification(message):
    """ Envía una notificación al tópico SNS """
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject="🚨 Incident Response Triggered"
        )
        logger.info(f"📢 SNS notification sent: {message}")
    except Exception as e:
        logger.error(f"❌ Failed to send SNS notification: {str(e)}")

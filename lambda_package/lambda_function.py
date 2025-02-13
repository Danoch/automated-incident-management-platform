import json
import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize EC2 client
ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    logger.info("🚀 Lambda function has started execution.")
    logger.info(f"📥 Event received: {json.dumps(event)}")

    for record in event.get("Records", []):
        if record.get("EventSource") == "aws:sns":
            try:
                sns_message = json.loads(record["Sns"]["Message"])  # Parse SNS message
                instance_id = sns_message.get("InstanceId", "UNKNOWN")
                state = sns_message.get("State", "UNKNOWN")

                if instance_id == "UNKNOWN":
                    logger.warning("⚠️ No instance ID found in the event.")
                    return

                logger.info(f"✅ Instance ID found: {instance_id}, Alarm State: {state}")

                if state == "ALARM":
                    stop_instance(instance_id)
                elif state == "OK":
                    start_instance(instance_id)
                else:
                    logger.warning(f"⚠️ Unrecognized state: {state}")

            except json.JSONDecodeError as e:
                logger.error(f"❌ Error decoding SNS message: {str(e)}")

def stop_instance(instance_id):
    """Stops the specified EC2 instance."""
    logger.info(f"🛑 Stopping EC2 instance: {instance_id}")
    try:
        response = ec2.stop_instances(InstanceIds=[instance_id])
        logger.info(f"✅ Instance {instance_id} stop initiated: {response}")
    except Exception as e:
        logger.error(f"❌ Error stopping instance {instance_id}: {str(e)}")

def start_instance(instance_id):
    """Starts the specified EC2 instance."""
    logger.info(f"🚀 Starting EC2 instance: {instance_id}")
    try:
        response = ec2.start_instances(InstanceIds=[instance_id])
        logger.info(f"✅ Instance {instance_id} start initiated: {response}")
    except Exception as e:
        logger.error(f"❌ Error starting instance {instance_id}: {str(e)}")

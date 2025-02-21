from google.cloud import pubsub_v1

from sync_secrets import syncSecretFromSource

def listen_to_pubsub(project_id, subscription_id, callback):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}...")
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()


def pubsub_callback(message):
    print(f"Received message: {message.data}")
    message.ack()
    
    # Trigger secret sync on message receipt
    syncSecretFromSource()

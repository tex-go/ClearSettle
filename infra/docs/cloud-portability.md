# Cloud Portability Architecture

ClearSettle's application layer is designed with cloud-portable abstractions
so the backend can migrate from GCP to AWS or Azure **without changing
application code** — only the infrastructure wiring changes.

---

## Portability Interfaces

### StorageProvider

Abstraction for object storage operations.

```python
class StorageProvider(Protocol):
    async def upload_file(
        self,
        file_obj: BinaryIO,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file and return the stored path or URI."""

    async def download_file(
        self,
        source_path: str,
    ) -> bytes:
        """Download file contents."""

    async def delete_file(self, path: str) -> None:
        """Delete file."""

    async def generate_signed_url(
        self,
        path: str,
        expiry_seconds: int = 3600,
        method: str = "GET",
    ) -> str:
        """Generate a time-limited pre-signed URL."""
```

| Method | GCP | AWS | Azure |
|---|---|---|---|
| `upload_file` | `storage.Client().bucket().blob().upload_from_file()` | `s3.put_object()` | `BlobServiceClient.upload_blob()` |
| `download_file` | `blob.download_as_bytes()` | `s3.get_object()['Body'].read()` | `blob.download_blob().readall()` |
| `delete_file` | `blob.delete()` | `s3.delete_object()` | `blob.delete_blob()` |
| `generate_signed_url` | `blob.generate_signed_url()` | `s3.generate_presigned_url()` | `generate_blob_sas()` |

Current implementation: `services/storage/storage_service.py`

#### GCP (current)
```python
class GCSStorageService(StorageProvider):
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(os.environ["GCS_BUCKET_NAME"])
```

#### AWS migration
```python
class S3StorageService(StorageProvider):
    def __init__(self):
        self.client = boto3.client("s3")
        self.bucket_name = os.environ["S3_BUCKET_NAME"]
```

#### Azure migration
```python
class AzureBlobStorageService(StorageProvider):
    def __init__(self):
        self.client = BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        )
        self.container = os.environ["AZURE_CONTAINER_NAME"]
```

Switch provider via `STORAGE_BACKEND` env var — no application code changes needed.

---

### EventBus

Abstraction for asynchronous event publishing and subscription.

```python
class EventBus(Protocol):
    async def publish(
        self,
        topic: str,
        payload: dict,
        attributes: dict[str, str] | None = None,
    ) -> str:
        """Publish event and return message ID."""

    async def subscribe(
        self,
        subscription: str,
        handler: Callable[[dict], Awaitable[None]],
        max_messages: int = 10,
    ) -> None:
        """Pull and process messages from a subscription."""
```

| Method | GCP Pub/Sub | AWS SQS/SNS | Azure Service Bus |
|---|---|---|---|
| `publish` | `PublisherClient.publish()` | `sns.publish()` | `ServiceBusClient.send_messages()` |
| `subscribe` | `SubscriberClient.pull()` | `sqs.receive_message()` | `receiver.receive_messages()` |

Current implementation: publish via Pub/Sub REST API (invoked by Cloud Scheduler → push subscriptions → Cloud Run).

#### GCP (current)
```python
class PubSubEventBus(EventBus):
    async def publish(self, topic: str, payload: dict, **kwargs) -> str:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, topic)
        data = json.dumps(payload).encode("utf-8")
        future = publisher.publish(topic_path, data)
        return future.result()
```

#### AWS migration
```python
class SQSEventBus(EventBus):
    async def publish(self, topic: str, payload: dict, **kwargs) -> str:
        response = boto3.client("sqs").send_message(
            QueueUrl=os.environ[f"SQS_{topic.upper()}_URL"],
            MessageBody=json.dumps(payload),
        )
        return response["MessageId"]
```

---

### SecretProvider

Abstraction for reading runtime secrets.

```python
class SecretProvider(Protocol):
    async def get_secret(
        self,
        secret_name: str,
        version: str = "latest",
    ) -> str:
        """Retrieve secret value as string."""
```

| Method | GCP Secret Manager | AWS Secrets Manager | Azure Key Vault |
|---|---|---|---|
| `get_secret` | `SecretManagerServiceClient.access_secret_version()` | `secretsmanager.get_secret_value()` | `SecretClient.get_secret()` |

In practice, Cloud Run injects secrets directly as environment variables, so
`os.environ["DB_PASSWORD"]` works on all clouds — the SecretProvider pattern
is mainly for application-initiated secret rotation or dynamic lookups.

---

### NotificationProvider

Abstraction for sending transactional notifications.

```python
class NotificationProvider(Protocol):
    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body_html: str,
        body_text: str | None = None,
        from_address: str | None = None,
    ) -> str:
        """Send transactional email. Returns message ID."""

    async def send_webhook(
        self,
        url: str,
        payload: dict,
        headers: dict[str, str] | None = None,
        timeout_seconds: int = 10,
    ) -> int:
        """Send HTTP webhook POST. Returns HTTP status code."""
```

| Method | GCP (Sendgrid/SMTP) | AWS SES | Azure Communication Services |
|---|---|---|---|
| `send_email` | `sendgrid.SendGridAPIClient.send()` | `ses.send_email()` | `EmailClient.begin_send()` |
| `send_webhook` | `httpx.AsyncClient.post()` | `httpx.AsyncClient.post()` | `httpx.AsyncClient.post()` |

Webhooks use plain HTTPS — identical across all clouds.

---

## Migration Playbook

### GCP → AWS

1. **Compute:** Replace Cloud Run with **AWS App Runner** or **ECS Fargate**.
   - Both support container images, scale-to-zero (App Runner), and VPC access.

2. **Database:** Replace Cloud SQL with **Amazon RDS PostgreSQL**.
   - No application code changes — same `asyncpg` / SQLAlchemy driver.
   - Update `DB_HOST` environment variable.

3. **Storage:** Replace GCS with **S3**.
   - Swap `GCSStorageService` → `S3StorageService` via `STORAGE_BACKEND=s3`.

4. **Events:** Replace Pub/Sub with **SQS + SNS** or **EventBridge**.
   - Swap `PubSubEventBus` → `SQSEventBus` via `EVENT_BACKEND=sqs`.

5. **Secrets:** Replace Secret Manager with **AWS Secrets Manager**.
   - Environment variable injection remains the same pattern.

6. **Scheduler:** Replace Cloud Scheduler with **Amazon EventBridge Scheduler**.

### GCP → Azure

1. **Compute:** Replace Cloud Run with **Azure Container Apps**.
   - Supports Dapr, KEDA scaling, and VNET integration.

2. **Database:** Replace Cloud SQL with **Azure Database for PostgreSQL Flexible Server**.

3. **Storage:** Replace GCS with **Azure Blob Storage**.
   - Swap `GCSStorageService` → `AzureBlobStorageService` via `STORAGE_BACKEND=azure`.

4. **Events:** Replace Pub/Sub with **Azure Service Bus**.

5. **Secrets:** Replace Secret Manager with **Azure Key Vault**.

6. **Scheduler:** Replace Cloud Scheduler with **Azure Logic Apps** or **Container Apps Jobs** with KEDA.

---

## Environment Variable Portability Matrix

| Variable | GCP Value | AWS Value | Azure Value |
|---|---|---|---|
| `STORAGE_BACKEND` | `gcs` | `s3` | `azure` |
| `GCS_BUCKET_NAME` | `clearsettle-prod-reports` | — | — |
| `S3_BUCKET_NAME` | — | `clearsettle-prod-reports` | — |
| `AZURE_CONTAINER_NAME` | — | — | `clearsettle-prod-reports` |
| `EVENT_BACKEND` | `pubsub` | `sqs` | `servicebus` |
| `DB_HOST` | Cloud SQL private IP | RDS endpoint | PostgreSQL FQDN |
| `SMTP_BACKEND` | `sendgrid` | `ses` | `azure_comms` |

All other application environment variables are cloud-neutral.

---

## Infrastructure as Code Portability

Terraform modules in this repository are **GCP-specific** but follow
consistent patterns that map 1:1 to equivalent resources on AWS/Azure:

| Module | GCP Resource | AWS Equivalent | Azure Equivalent |
|---|---|---|---|
| `modules/cloudrun` | `google_cloud_run_v2_service` | `aws_apprunner_service` | `azurerm_container_app` |
| `modules/cloudrun-job` | `google_cloud_run_v2_job` | `aws_batch_job_definition` | `azurerm_container_app_job` |
| `modules/pubsub` | `google_pubsub_topic` | `aws_sqs_queue` + `aws_sns_topic` | `azurerm_servicebus_namespace` |
| `modules/scheduler` | `google_cloud_scheduler_job` | `aws_scheduler_schedule` | `azurerm_logic_app_trigger_recurrence` |
| `modules/cloud_sql` | `google_sql_database_instance` | `aws_db_instance` | `azurerm_postgresql_flexible_server` |
| `modules/storage` | `google_storage_bucket` | `aws_s3_bucket` | `azurerm_storage_account` |
| `modules/secrets` | `google_secret_manager_secret` | `aws_secretsmanager_secret` | `azurerm_key_vault_secret` |
| `modules/budget` | `google_billing_budget` | `aws_budgets_budget` | `azurerm_consumption_budget_subscription` |

To migrate infrastructure: re-implement these modules targeting the new
provider, keeping the same variable interface. Environment-level `main.tf`
files call the same module signatures — only the module source paths change.

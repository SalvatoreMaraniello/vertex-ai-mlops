## Storage

```python
gcs = storage.Client(project = PROJECT_ID)

# create (if not exist)
if not gcs.lookup_bucket(BUCKET):
    bucketDef = gcs.bucket(BUCKET)
    bucket = gcs.create_bucket(bucketDef, project=PROJECT_ID, location=REGION)
    print(f'Created Bucket: {gcs.lookup_bucket(BUCKET).name}')
else:
    bucket = gcs.bucket(BUCKET)
    print(f'Bucket already exist: {bucket.name}')

# list blobs
list(bucket.list_blobs(prefix = f'bucket-name-prefix'))

# upload a file to blob (if not exists)
file_name = 'dummy.json'
local_path = 'path to folder containing file'
blob_path = 'blob gsutil path without gs://BUCKET/'
storage_client = storage.Client()
bucket = gcs.bucket(BUCKET)
blob = bucket.blob(f"{blob_path}/{file_name}")
if not blob.exists():
    blob.upload_from_filename(f"{local_path}/{file_name}")
```


## Bigquery

Plenty of Python snippets are found at https://cloud.google.com/bigquery/docs/samples/bigquery-list-datasets

```python
from google.cloud import bigquery

# set a client
bq = bigquery.Client()

# list datasets (and pick one)
ds_list = list(bq.list_datasets())
ds = ds_list[0]

# list tables in dataset
tab_list = list(bq.list_tables(ds.dataset_id))
tab = tab_list[0]

# query to Pandas
pred = bq.query(
    query = f"SELECT * FROM {ds.dataset_id}.{tab.} LIMIT 10"
).to_dataframe()

```


## AI Platform

Plenty more snippets can be found on https://cloud.google.com/python/docs/reference.

```python
from google.cloud import aiplatform
PROJECT_ID = os.popen('gcloud config get-value project').read()[:-1]
REGION = 'europe-west2'

# initialisation (nothing will work otherwise)
aiplatform.init(project=PROJECT_ID, location=REGION)

# create dataset (from BQ table)
dataset = aiplatform.TabularDataset.create(
    display_name = 'MyDataset', 
    bq_source = f'bq://{PROJECT_ID}.{DATASET}.{TABLE}', # create from BQ table,
    # gcs_source=['gs://path/to/my/dataset.csv']        # create from storage
    labels = {'notebook':f'{NOTEBOOK}'}
)

# List datasets
datasets_list = aiplatform.TabularDataset.list(
    project=PROJECT_ID, location=REGION, filter='display_name="NAME"')
for dd in datasets_list:
    print(f'{dd.display_name}: {dd.name}')

# get datasets (you need the dataset name, not diplay name used above!)
dataset = aiplatform.TabularDataset( dataset_name = '19372784921038', project = PROJECT_ID)

# delete it
dataset.delete()

# Set a train job using AutoML
job = training_jobs.AutoMLTabularTrainingJob(
    display_name="my_display_name",
    optimization_prediction_type="classification",
    optimization_objective="minimize-log-loss",
    column_specs={"column_1": "auto", "column_2": "numeric"},
    labels={'key': 'value', 'another_key': 'another_value'},
)

# list models
models_list = aiplatform.Model.list()
for model in models_list:
    print(f"DISPLAY NAME: {model.display_name}. MODEL_ID: {model.name}")

# Get a model
model = aiplatform.Model('/projects/my-project/locations/us-central1/models/{MODEL_ID}')

### List/Get a model evaluation (and some metrics)
evaluations_list = model.list_model_evaluations()
evaluation = evaluations[0]
# evaluation = model.get_model_evaluation( eval_id or evaluation.name)
for metric, value in evaluation.metrics.items():
    if metric == 'confidenceMetrics':
        continue
    print(f"{metric},{value}")

for i in range(len(geteval.metrics['confusionMatrix']['annotationSpecs'])):
    print('True Label = ', geteval.metrics['confusionMatrix']['annotationSpecs'][i]['displayName'], ' has Predicted labels = ', geteval.metrics['confusionMatrix']['rows'][i])
    
### List/Get evaluation slices (we need a different client)
model_client = aiplatform.gapic.ModelServiceClient(
    client_options={"api_endpoint": f'{REGION}-aiplatform.googleapis.com'})

slices_list = model_client.list_model_evaluation_slices(
    # str like 'projects/PROJECT-ID/locations/REGION/models/MODEL-ID/evaluations/EVAL-ID'
    parent=model_client.model_evaluation_path(
        project=PROJECT_ID, location=REGION, model=model.name, evaluation=evaluation.name
    )
)
for me_slice in response:
    print("model_evaluation_slice:", me_slice)
```

## Kuberflow and Vertex AI Pipelines

Google provides pre-built components under module `google_cloud_pipeline_components`. See https://cloud.google.com/vertex-ai/docs/pipelines/components-introduction or also https://cloud.google.com/vertex-ai/docs/pipelines/notebooks or the components reference list https://cloud.google.com/vertex-ai/docs/pipelines/gcpc-list.

```python
import kfp
@kfp.dsl.pipeline(
    name = f'kfp-{NOTEBOOK}-{DATANAME}-{TIMESTAMP}',
    description = "A description"
    # root dir to generate in/output under this pipeline. It's the address to a blob in a pre-existing bucket.
    pipeline_root = f"gs://{BUCKET}/a/path")
def my_pipeline(
    my_inputs: str,
    can_be: dict,
    anything: int):
    """Objects in here are kfp components. Any piece of code outside a component object is evaluated
    only once at compile time - and won't change in the future."""
    
    
    # dataset
    dataset = gcc_aip.TabularDatasetCreateOp(
        # Inputs are the same as aiplatform.TabularDataset.create. 
        # Output is different though.
        project = project, display_name = display_name,
        bq_source = bq_source, labels = labels
    )
    


```


## Service accounts

These are all CLI snippets

```python
PROJECT_ID = os.popen('gcloud config get-value project').read()[:-1]

# see who's executing the code
SERVICE_ACCOUNT = os.popen("gcloud config list --format='value(core.account)'").read()[:-1]

# view all roles
roles = os.popen(
    f"""gcloud projects get-iam-policy {PROJECT_ID} --filter="bindings.members:{SERVICE_ACCOUNT}" --format='table(bindings.role)' --flatten="bindings[].members" """).read().replace('ROLE','').replace('roles/','')
roles = [rr for rr in roles.split('\n') if rr!='']
```

## Secrets

You find all code snippets either https://cloud.google.com/secret-manager/docs/samples/ or https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets. Here is worth remembering that a secret is a wrapper for a secret version. The secret version object is the one that actually contains a value (payload).

When adding values to secrets versions, you can optionally add checksum for data integrity assurance. This roughly works as follows:
- Gcriven a payload, you create a hash associated to it.
- You load the hash with the payload.
- When you retrieve the payload, you recompute the hash and check if it matches.
For a nice read on hash functions and tables, see https://thepythoncorner.com/posts/2020-08-21-hash-tables-understanding-dictionaries/.

```python
import os
from google.cloud import secretmanager
import google_crc32c

secret_id = 'DUMMY_SECRET'
payload = 'DUMMY VALUE' # this is the secret (version) value
project_id = os.popen('gcloud config get-value project').read()[:-1]

# Create the Secret Manager client.
client = secretmanager.SecretManagerServiceClient()

### --- Create the secret (the secret has no value at this stage).
# PS: we should first check the secret exists - see list secrets below.
# Build the resource name of the parent project.
parent = f"projects/{project_id}"
# make request
response = client.create_secret(
    request={
        "parent": parent, 
        "secret_id": secret_id,
        "secret": {"replication": {"automatic": {}}},
    }
)

### --- list secrets
for secret in client.list_secrets(
    request={
        "parent": parent, 
        "filter": secret_id # optional
    }):
    print("Found secret: {}".format(secret.name))
    
### --- get a secret
# Build the resource name of the secret.
secret_path = client.secret_path(project_id, secret_id)
# Get the secret.
secret = client.get_secret(request={"name": secret_path})

### --- Add secret version
# calc payload checksum
crc32c = google_crc32c.Checksum()
payload = payload.encode("UTF-8")
crc32c.update(payload)
# Add the secret version.
version = client.add_secret_version(
    request={
        "parent": secret_path,
        "payload": {"data": payload, "data_crc32c": int(crc32c.hexdigest(), 16)},
    }
)

### --- Get secret version (this gives no access to payload)
version_id = "latest" # or "number"
name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
# Get the secret version.
version = client.get_secret_version(request={"name": name})

### --- Access secret payload
# Access the secret version.
response = client.access_secret_version(request={"name": name})
# verify payload checksum. Note crc32c is reallocated
# as hash is salted - see Ref. [1]
crc32c = google_crc32c.Checksum()
crc32c.update(response.payload.data)
if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
    print("Data corruption detected.")
# get payload
payload = response.payload.data.decode("UTF-8")
```


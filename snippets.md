## Buckets

```python
gcs = storage.Client(project = PROJECT_ID)

# create (if not exist)
if not gcs.lookup_bucket(BUCKET):
    bucketDef = gcs.bucket(BUCKET)
    bucket = gcs.create_bucket(bucketDef, project=PROJECT_ID, location=REGION)
    print(f'Created Bucket: {gcs.lookup_bucket(BUCKET).name}')
else:
    bucketDef = gcs.bucket(BUCKET)
    print(f'Bucket already exist: {bucketDef.name}')

# list blobs
list(bucketDef.list_blobs(prefix = f'a/prpwd
                          efix'))
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

```python
from google.cloud import aiplatform

# initialisation (nothing will work otherwise)
aiplatform.init(project=PROJECT_ID, location=REGION)
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


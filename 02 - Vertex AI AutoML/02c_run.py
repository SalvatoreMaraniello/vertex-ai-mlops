"""
Notebook 02c (most of) in a script.

Highlights:
- Build a training pipeline in AI platform.
- Pipeline uses Kuberflow and Google Cloud Pipeline (buill-in) components
"""

import os 
import json
import shutil
import requests
import numpy as np
from datetime import datetime

import kfp
from google.cloud import aiplatform, bigquery, storage
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from google.cloud.secretmanager import SecretManagerServiceClient
from google_cloud_pipeline_components import aiplatform as gcc_aip

### --- Set Uu

# params
PROJECT_ID = os.popen('gcloud config get-value project').read()[:-1]
SERVICE_ACCOUNT = os.popen("""gcloud config list --format='value(core.account)' """).read()[:-1]

smc = SecretManagerServiceClient()
REGION = smc.access_secret_version(
    request={"name": f"projects/{PROJECT_ID}/secrets/PARAM_REGION/versions/latest"}
).payload.data.decode("UTF-8")
DATANAME = 'fraud'
NOTEBOOK = '02c'


# model params
MODEL_VARS = {
    'target': ['Class'],      
    'omit': ['transaction_id', 'splits']
}
BUCKET = PROJECT_ID
URI = f"gs://{BUCKET}/{DATANAME}/models/{NOTEBOOK}"
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")
DIR = f"temp/{NOTEBOOK}"

# environment
os.system(f"rm -rf {DIR}")
os.system(f"mkdir -p {DIR}")


### clean up datasets built in previous attempts
aiplatform.init(project=PROJECT_ID, location=REGION)

for dd in aiplatform.TabularDataset.list(
    project=PROJECT_ID, location=REGION, 
    filter=f'display_name="{NOTEBOOK}_{DATANAME}"'
    ):
    dd.delete()
    print(f'Deleted {dd.display_name}: {dd.name}')


### Build pipeline
@kfp.dsl.pipeline(
    name = f'kfp-{NOTEBOOK}-{DATANAME}-{TIMESTAMP}',
    description = "A pipeline for building a dataset, creating, training and deploying a ML model",
    # root dir to generate in/output under this pipeline
    pipeline_root = URI+'/kfp/'
)
def train_deploy_pipeline(
    # these variables are 100% user-defined
    project: str,
    dataname: str,
    display_name: str,
    deploy_machine: str,
    bq_source: str,
    location: str,
    var_split: str, 
    var_target: str,
    features_spec: dict,
    labels: dict):
    
    ### create dataset
    # For testing/debug, try aiplatform.TabularDataset with same arguments
    dataset = gcc_aip.TabularDatasetCreateOp(
        project = project,
        location = location,
        display_name = display_name,
        bq_source = bq_source,
        labels = labels
    )
    
    # training
    model = gcc_aip.AutoMLTabularTrainingJobRunOp(
        project = project,
        location = REGION,
        display_name = display_name,
        optimization_prediction_type = "classification",
        optimization_objective = "maximize-au-prc",
        budget_milli_node_hours = 1000,
        disable_early_stopping=False,
        column_specs = features_spec,
        dataset = dataset.outputs['dataset'],
        target_column = var_target,
        predefined_split_column_name = var_split,
        labels = labels
    )
    
    # Endpoint: Creation
    endpoint = gcc_aip.EndpointCreateOp(
        project = project,
        location = REGION,
        display_name = display_name,
        labels = labels
    )
    
    # Endpoint: Deployment of Model
    deployment = gcc_aip.ModelDeployOp(
        model = model.outputs["model"],
        endpoint = endpoint.outputs["endpoint"],
        dedicated_resources_min_replica_count = 1,
        dedicated_resources_max_replica_count = 1,
        traffic_split = {"0": 100},
        dedicated_resources_machine_type= deploy_machine
    )
    
# compile to local path
kfp.v2.compiler.Compiler().compile(
    pipeline_func = train_deploy_pipeline,
    package_path = f"{DIR}/{NOTEBOOK}.json"
)

# move compiled pipeline to GCS blob (replace if exists)
gcs = storage.Client()
bucket = gcs.bucket(BUCKET)
blob = bucket.blob(f"{DATANAME}/models/{NOTEBOOK}/kfp/{NOTEBOOK}.json")
# if not blob.exists():
#     pass
blob.upload_from_filename(f"{DIR}/{NOTEBOOK}.json")


### Crete pipeline job
# Step 1 is to define all input required by train_pipeline. This includes
# fetching a list of features/target variables.

# get feature spec dictionary
from google.cloud import bigquery
bigquery = bigquery.Client(project = PROJECT_ID)
features_list = bigquery.query(
    f"""SELECT column_name 
    FROM {DATANAME}.INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = '{DATANAME}_prepped'"""
).to_dataframe()['column_name'].values.tolist()
features_list = list(
    set(features_list) - set(MODEL_VARS['target'] + MODEL_VARS['omit'])
)

# Define
pipeline = aiplatform.PipelineJob(
    location = REGION, 
    display_name = f'{NOTEBOOK}_{DATANAME}',
    template_path = f"{URI}/kfp/{NOTEBOOK}.json", # path to pipeline json
    parameter_values = {
        "project" : PROJECT_ID,
        "dataname" : DATANAME,
        "display_name" : f'{NOTEBOOK}_{DATANAME}',
        "deploy_machine" : 'n1-standard-2',
        "location": REGION,
        "bq_source" : f'bq://{PROJECT_ID}.{DATANAME}.{DATANAME}_prepped',
        "var_target" : MODEL_VARS['target'][0],
        "var_split": "splits",
        "features_spec" : dict.fromkeys(features_list, 'auto'),
        "labels" : {'notebook': NOTEBOOK}       
    },
    labels = {'notebook': NOTEBOOK},
    enable_caching=False
)


# Launch
SERVICE_ACCOUNT = os.popen("""gcloud config list --format='value(core.account)' """).read()[:-1]
response = pipeline.run(
    service_account = SERVICE_ACCOUNT
)
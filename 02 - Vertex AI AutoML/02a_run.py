"""
Notebook 02a (most of) in a script.

Highlights:
- Shows how to post to endpoint and get predictions in a few different ways.
- The script assumes we have (manually) deployed a ML model
"""

import os 
from google.cloud import aiplatform
from google.cloud import bigquery
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
import json
import requests

# Params
PROJECT_ID = os.popen('gcloud config get-value project').read()[:-2]
REGION = 'europe-west2'
DATANAME = 'fraud'
NOTEBOOK = '02a'

# init clients/sdk
aiplatform.init(project=PROJECT_ID, location=REGION)
bq = bigquery.Client()

# Let's pull some data from BigQuery (will be used for prediction later)
pred = bq.query(
    query = f"SELECT * FROM {DATANAME}.{DATANAME}_prepped WHERE splits='TEST' LIMIT 10"
).to_dataframe()
pred = pred.drop(columns=['Class', 'transaction_id'], errors='ignore')
pred['Time'] = pred['Time'].apply(str)

# reshape to a dict format (and later to json so we can send to model for evaluation)
newob = pred.to_dict(orient='records')

# call using aiplatform functions
endpoint = aiplatform.Endpoint.list(project=PROJECT_ID, filter=f'display_name={NOTEBOOK}')[0]
instances = [json_format.ParseDict(nn, Value()) for nn in newob]
parameters = json_format.ParseDict({}, Value())
predictions = endpoint.predict(instances=instances, parameters=parameters)
explanations = endpoint.explain(instances=instances, parameters=parameters)

# call using requests
r = requests.post(
    f'https://{REGION}-aiplatform.googleapis.com/v1/{endpoint.resource_name}:predict',
    data = json.dumps({"instances": newob}),
    headers = {
        "Authorization": "Bearer " + os.popen('gcloud auth application-default print-access-token').read()[:-2],
        "Content-Type": "application/json; charset=utf-8"
    }
)
predictions_dict = json.loads(r.content)

# explain prediction
record_number = 0 # up to len(pred)-1
features = []
scores = []
for k in explanation.explanations[record_number].attributions[0].feature_attributions:
    features.append(k)
    scores.append(explanation.explanations[record_number].attributions[0].feature_attributions[k])
features = [x for _, x in sorted(zip(scores, features))]
scores = sorted(scores)


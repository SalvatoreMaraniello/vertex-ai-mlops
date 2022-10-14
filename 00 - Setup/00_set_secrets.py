"""
In this file we use GCP secrets manager to set some parameters that will be available for the whole projects.
The code in this script relies on Python snippets from https://cloud.google.com/secret-manager/docs/samples.

Note: 
    These are not "real secrets", hence their value is hardcoded in this script. Do not do this in a real deployment.

Important: 
    To use secret manager, run:
        ```pip install google.cloud.secret-manager```
    To access secrets versions, you'll need Secret manager Secret Accessor privileges.
"""


# Import the Secret Manager client library.
from google.cloud import secretmanager
import import goo


def create_secret(project_id, secret_id) -> secretmanager.Secret:
    """
    Create a new secret with the given name. A secret is a logical wrapper
    around a collection of secret versions. Secret versions hold the actual
    secret material.
    """

    # Import the Secret Manager client library.
    from google.cloud import secretmanager

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the parent project.
    parent = f"projects/{project_id}"

    # check if exists
    candidate_secrets = [
        ss for ss in client.list_secrets(request={"parent": parent, "filter": secret_id})
        if ss.name.split('/')[-1] == secret_id
    ]

    if candidate_secrets:
        if len(candidate_secrets)>1:
            raise ValueError("Something went wrong: we were expecting at most 1 secret. More were found.")
        print( f"Secret already exists under name {candidate_secrets[0].name}")
        return candidate_secrets[0]

    # Create the secret.
    response = client.create_secret(
        request={
            "parent": parent,
            "secret_id": secret_id,
            "secret": {"replication": {"automatic": {}}},
        }
    )        
    # Print the new secret name.
    print("Created secret: {}".format(response.name))
    
    return response


def add_secret_version(project_id, secret_id, payload):
    """
    Add a new secret version to the given secret with the provided payload.
    """

    # Import the Secret Manager client library.
    from google.cloud import secretmanager
    import google_crc32c

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the parent secret.
    parent = client.secret_path(project_id, secret_id)

    # Convert the string payload into a bytes. This step can be omitted if you
    # pass in bytes instead of a str for the payload argument.
    payload = payload.encode("UTF-8")

    # # Calculate payload checksum. Passing a checksum in add-version request
    # # is optional. Requires google-crc32c
    crc32c = google_crc32c.Checksum()
    crc32c.update(payload)

    # Add the secret version.
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {"data": payload, "data_crc32c": int(crc32c.hexdigest(), 16)},
        }
    )

    # Print the new secret version name.
    print("Added secret version: {}".format(response.name))

    
def access_secret_version(project_id, secret_id, version_id):
    """
    Access the payload for the given secret version if one exists. The version
    can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
    """

    # Import the Secret Manager client library.
    from google.cloud import secretmanager

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Verify payload checksum.
    crc32c = google_crc32c.Checksum()
    crc32c.update(response.payload.data)
    if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
        print("Data corruption detected.")
        return response

    # Print the secret payload.
    #
    # WARNING: Do not print the secret in a production environment - this
    # snippet is showing how to access the secret material.
    payload = response.payload.data.decode("UTF-8")
    print("Plaintext: {}".format(payload))


if __name__ == "__main__":

    import os
    # Projects Parameters
    parameters = {
        "PARAM_REGION": "europe-west2"
    }
    PROJECT_ID = os.popen('gcloud config get-value project').read()[:-1]
            
    client = secretmanager.SecretManagerServiceClient()

    for param_name, param_val in parameters.items():
        # create secret and return 
        response = create_secret(PROJECT_ID, param_name)
        secret_path = client.secret_path(PROJECT_ID, param_name)
        versions = list(client.list_secret_versions( request={"parent": secret_path}))
        
        if versions:
            print(f"A version for {secret_path} was found. We won't add a new one.")
        else:
            # add value only if secret has just been created
            add_secret_version(PROJECT_ID, param_name, param_val)
        
        # sample code: access secret value
        access_secret_version(PROJECT_ID, param_name, "latest")
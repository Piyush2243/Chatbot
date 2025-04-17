# Note: DALL-E 3 requires version 1.0.0 of the openai-python library or later
import os
import openai
import json

client = openai.AzureOpenAI(
    api_version="YOUR-AZURE-API-VERSION",
    azure_endpoint="YOUR-AZURE-ENDPOINT",  # Replace with your Azure OpenAI endpoint
    api_key='YOUR-AZURE-API-KEY',  # Replace with your Azure OpenAI API key
)

result = client.images.generate(
    model="dall-e-3", # the name of your DALL-E 3 deployment
    prompt="create an image of a dog",
    n=1
)

image_url = json.loads(result.model_dump_json())['data'][0]['url']
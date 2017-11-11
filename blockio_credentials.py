import json


class BlockIOCredentials():
    def __init__(self, filepath):
        # Load Block IO credentials from the given JSON file
        # Requires 'api_key' and 'secret_pin' to be specified
        with open(filepath) as data_file:    
             data = json.load(data_file)
        
        self.api_key = data['api_key']
        self.secret_pin = data['secret_pin']

import json


class FacebookCredentials():
    def __init__(self, filepath):
        # Load Facebook credentials from the given JSON file
        # Requires 'secret' and 'id' to be specified
        with open(filepath) as data_file:    
             data = json.load(data_file)

        self.id = data['id']
        self.secret = data['secret']

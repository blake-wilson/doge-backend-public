import urllib.request
from rauth import OAuth1Service
from rauth import OAuth2Service
from flask import url_for
from flask import current_app
from flask import redirect
from flask import request
from flask import session
import json


def new_decoder(payload):
    return json.loads(payload.decode('utf-8'))


class OAuthSignIn(object):
    providers = None

    def __init__(self, provider_name):
        self.provider_name = provider_name
        credentials = current_app.config['OAUTH_CREDENTIALS'][provider_name]
        self.consumer_id = credentials['id']
        self.consumer_secret = credentials['secret']

    def authorize(self):
        pass

    def callback(self):
        pass

    def get_callback_url(self):
        return url_for('oauth_callback', provider=self.provider_name,
                       _external=True)

    @classmethod
    def get_provider(self, provider_name):
        if self.providers is None:
            self.providers = {}
            for provider_class in self.__subclasses__():
                provider = provider_class()
                self.providers[provider.provider_name] = provider
        return self.providers[provider_name]


class FacebookSignIn(OAuthSignIn):
    def __init__(self):
        super(FacebookSignIn, self).__init__('facebook')
        self.service = OAuth2Service(
            name='facebook',
            client_id=self.consumer_id,
            client_secret=self.consumer_secret,
            authorize_url='https://graph.facebook.com/oauth/authorize',
            access_token_url='https://graph.facebook.com/oauth/access_token',
            base_url='https://graph.facebook.com/'
        )

    def authorize(self):

        return redirect(self.service.get_authorize_url(
            scope='email,user_friends',
            response_type='code',
            redirect_uri=self.get_callback_url())
        )

    def callback(self):
        if 'code' not in request.args:
            return None, None, None
        oauth_session = self.service.get_auth_session(
            decoder=new_decoder,
            data={'code': request.args['code'],
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.get_callback_url()}
        )
        me = oauth_session.get('me').json()
        access_token = oauth_session.access_token
        session['access_token'] = access_token
        return 'facebook$' + me['id'], me['name']

# class TwitterSignIn(OAuthSignIn):
#     def __init__(self):
#         super(TwitterSignIn, self).__init__('twitter')
#         self.service = OAuth1Service(
#             name='twitter',
#             consumer_key=self.consumer_id,
#             consumer_secret=self.consumer_secret,
#             request_token_url='https://api.twitter.com/oauth/request_token',
#             authorize_url='https://api.twitter.com/oauth/authorize',
#             access_token_url='https://api.twitter.com/oauth/access_token',
#             base_url='https://api.twitter.com/1.1/'
#         )

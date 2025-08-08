# !/usr/bin/env python3
"""
    xpan auth
    include:
        authorization_code, just get token by code
        refresh_token
        device_code
"""
import os,sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
import openapi_client
from openapi_client.api import auth_api
from openapi_client.model.oauth_token_authorization_code_response import OauthTokenAuthorizationCodeResponse
from openapi_client.model.oauth_token_refresh_token_response import OauthTokenRefreshTokenResponse
from pprint import pprint

def get_code(config:dict) -> str:
    print("Please visit the following URL to authorize:")
    print(f"https://openapi.baidu.com/oauth/2.0/authorize?response_type=code&client_id={config['AppKey']}&redirect_uri=oob&scope=basic,netdisk&device_id={config['AppID']}")
    print("After authorizing, you will receive a code. Please enter it here:")
    code = input("Enter the code: ")
    return code.strip()

def oauthtoken_authorizationcode(config:dict,code:str) -> str:
    """
    authorizationcode
    get token by authorization code
    """
    # Enter a context with an instance of the API client
    with openapi_client.ApiClient() as api_client:
        # Create an instance of the API class
        api_instance = auth_api.AuthApi(api_client)
        client_id = config['AppKey'] # str | 
        client_secret = config['SecretKey'] # str | 
        redirect_uri = "oob" # str | 

        # example passing only required values which don't have defaults set
        try:
            api_response = api_instance.oauth_token_code2token(code, client_id, client_secret, redirect_uri)
            pprint(api_response.refresh_token)
            return api_response.refresh_token
        except openapi_client.ApiException as e:
            print("Exception when calling AuthApi->oauth_token_code2token: %s\n" % e)


def oauthtoken_refreshtoken(config:dict,refresh_token:str) -> str:
    """
    refresh access token
    """
    # Enter a context with an instance of the API client
    with openapi_client.ApiClient() as api_client:
        # Create an instance of the API class
        api_instance = auth_api.AuthApi(api_client)
        # refresh_token = "122.5d587a6620cf03ebd221374097d5342a.Y3l9RzmaC4A1xq2F4xQtCnhIb4Ecp0citCARk0T.Uk3m_w" # str | 
        client_id = config['AppKey'] # str | 
        client_secret = config['SecretKey'] # str | 

        # example passing only required values which don't have defaults set
        try:
            api_response = api_instance.oauth_token_refresh_token(refresh_token, client_id, client_secret)
            print("A:",api_response)
            print(api_response.access_token,api_response.refresh_token)
            return api_response.access_token, api_response.refresh_token
        except openapi_client.ApiException as e:
            print("Exception when calling AuthApi->oauth_token_refresh_token: %s\n" % e)





if __name__ == '__main__':
    """
    main
    """
    # print("xpan auth test")
    oauthtoken_authorizationcode()
    oauthtoken_refreshtoken()

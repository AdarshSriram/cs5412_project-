import json
import logging

import azure.functions as func


def main(req: func.HttpRequest,  msg: func.Out[str]) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    logging.warning('hook msg sent')
    req_body = json.dumps(req.get_json())
    msg.set(req_body)
    
    return func.HttpResponse(
        req_body,
        status_code=200)

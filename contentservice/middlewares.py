class UnproxyMiddleware(object):
    '''Set the REMOTE_ADDR and SERVER_NAME back to real ones when we are behind a proxy or NGINX.

    THe proxy server is responsible to storing real remote address and server name to HTTP Headers.
    HTTP Header      Value
    X-Real-IP        The real remote address of the client.
    X-Server-Name    The real name of the server.
    '''

    def process_request(self, request):
        if 'HTTP_X_REAL_IP' in request.META:
            request.META['REMOTE_ADDR'] = request.META['HTTP_X_REAL_IP']
        if 'HTTP_X_REAL_SERVER' in request.META:
            request.META['SERVER_NAME'] = request.META['HTTP_X_REAL_SERVER']
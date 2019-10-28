import http.server
http.server.test(HandlerClass=http.server.SimpleHTTPRequestHandler, port=8081,
    bind="192.168.1.37")
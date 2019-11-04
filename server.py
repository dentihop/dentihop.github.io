# -*- coding: utf-8 -*-
#

"""Simple HTTP Server for Brython Development.
Files are served from subdirectory www, except cgi scripts that are
served from subdirectory cgi-bin
"""


import io
import os
import time
from webbrowser import open_new_tab
import argparse
import email
import datetime
import urllib.parse
from http import HTTPStatus
import socketserver
from server_modular_send_head import CGIHTTPRequestHandler, test

import http.cookiejar
# Python might be built without zlib
try:
    import zlib
except ImportError:
    zlib = None

# Generators for HTTP compression

def _zlib_producer(fileobj, wbits):
    """Generator that yields data read from the file object fileobj,
    compressed with the zlib library.
    wbits is the same argument as for zlib.compressobj.
    """
    bufsize = 2 << 17
    producer = zlib.compressobj(wbits=wbits)
    with fileobj:
        while True:
            buf = fileobj.read(bufsize)
            if not buf: # end of file
                yield producer.flush()
                return
            yield producer.compress(buf)

def _gzip_producer(fileobj):
    """Generator for gzip compression."""
    return _zlib_producer(fileobj, 31)

def _deflate_producer(fileobj):
    """Generator for deflate compression."""
    return _zlib_producer(fileobj, 15)

class CompressedHandler(CGIHTTPRequestHandler):

    # List of commonly compressed content types, copied from
    # https://github.com/h5bp/server-configs-apache.
    compressed_types = [
        "application/atom+xml",
        "application/javascript",
        "application/json",
        "application/ld+json",
        "application/manifest+json",
        "application/rdf+xml",
        "application/rss+xml",
        "application/schema+json",
        "application/vnd.geo+json",
        "application/vnd.ms-fontobject",
        "application/x-font-ttf",
        "application/x-javascript",
        "application/x-web-app-manifest+json",
        "application/xhtml+xml",
        "application/xml",
        "font/eot",
        "font/opentype",
        "image/bmp",
        "image/svg+xml",
        "image/vnd.microsoft.icon",
        "image/x-icon",
        "text/cache-manifest",
        "text/css",
        "text/html",
        "text/javascript",
        "text/plain",
        "text/vcard",
        "text/vnd.rim.location.xloc",
        "text/vtt",
        "text/x-component",
        "text/x-cross-domain-policy",
        "text/xml"
    ]

    # Dictionary mapping an encoding (in an Accept-Encoding header) to a
    # generator of compressed data. By default, provided zlib is available,
    # the supported encodings are gzip and deflate.
    # Override if a subclass wants to use other compression algorithms.
    compressions = {}
    if zlib:
        compressions = {
            'deflate': _deflate_producer,
            'gzip': _gzip_producer,
            'x-gzip': _gzip_producer # alias for gzip
        }

    def guess_type(self, path):
        ctype = CGIHTTPRequestHandler.guess_type(self, path)
        # I had the case where the mimetype associated with .js in the Windows
        # registery was text/plain...
        if os.path.splitext(path)[1] == ".js":
            ctype = "application/javascript"
        return ctype

    def translate_path(self, path):
        """For paths starting with /cgi-bin/, serve from cgi_dir"""
        elts = path.split('/')
        if len(elts) > 1 and elts[0] == '' and elts[1] == 'cgi-bin':
            return os.path.join(cgi_dir,*elts[2:])
        return CGIHTTPRequestHandler.translate_path(self, path)

    def handle_compression(self, f):

        if self.ctype not in self.compressed_types:
            return f

        # Get accepted encodings ; "encodings" is a dictionary mapping
        # encodings to their quality ; eg for header "gzip; q=0.8",
        # encodings["gzip"] is set to 0.8
        accept_encoding = self.headers.get_all("Accept-Encoding", ())
        encodings = {}
        for accept in http.cookiejar.split_header_words(accept_encoding):
            params = iter(accept)
            encoding = next(params, ("", ""))[0]
            quality, value = next(params, ("", ""))
            if quality == "q" and value:
                try:
                    q = float(value)
                except ValueError:
                    # Invalid quality : ignore encoding
                    q = 0
            else:
                q = 1 # quality defaults to 1
            if q:
                encodings[encoding] = max(encodings.get(encoding, 0), q)

        compressions = set(encodings).intersection(self.compressions)
        compression = None
        if compressions:
            # Take the encoding with highest quality
            compression = max((encodings[enc], enc)
                for enc in compressions)[1]
        elif '*' in encodings and self.compressions:
            # If no specified encoding is supported but "*" is accepted,
            # take one of the available compressions.
            compression = list(self.compressions)[0]
        if compression:
            # If at least one encoding is accepted, send data compressed
            # with the selected compression algorithm.
            producer = self.compressions[compression]
            self.send_header("Content-Encoding", compression)
            if self.content_length < 2 << 18:
                # For small files, load content in memory
                with f:
                    content = b''.join(producer(f))
                self.content_length = len(content)
                return io.BytesIO(content)
            else:
                chunked = self.protocol_version >= "HTTP/1.1"
                if chunked:
                    # Use Chunked Transfer Encoding (RFC 7230 section 4.1)
                    self.content_length = None
                    self.send_header("Transfer-Encoding", "chunked")
                # Return a generator of pieces of compressed data
                return producer(f)

# IP 2a01:cb08:8f80:ed00:55b2:a195:cfad:5e75
test(HandlerClass=CompressedHandler,
     ServerClass=socketserver.ThreadingTCPServer,
     port=80)


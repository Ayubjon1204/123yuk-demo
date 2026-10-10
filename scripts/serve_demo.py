from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class DemoHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        path = urlsplit(path).path
        prefix = "/123yuk-demo"
        if path == prefix:
            path = "/"
        elif path.startswith(prefix + "/"):
            path = path[len(prefix):]
        else:
            return self.directory + "/__outside_project__"
        return super().translate_path(path)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8080), DemoHandler).serve_forever()

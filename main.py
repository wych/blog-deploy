from flask import Flask, request
import hashlib
import hmac
import secrets
import os
import threading

from utils import *

app = Flask(__name__)
config_path = os.environ['DEPLOY_CONFIG'] if os.environ.get('DEPLOY_CONFIG') else 'config.toml'
conf = Config.parse(config_path)
repo = Repo(conf)
builder = Builder(conf)
builder.gen_static()
builder.deploy()

mutex = threading.Lock()

@app.route(conf.listen_url, methods=['POST'])
def up2date():
    if not secrets.compare_digest(request.headers.get('X-Hub-Signature'), verify_signature(request.data, conf.secret_key)):
        return 'bad signature', 401
    def thread_task():
        mutex.acquire()

        repo.update()
        builder.gen_static()
        builder.deploy()
        
        mutex.release()
    threading.Thread(target=thread_task).start()
    return 'ok', 200

def verify_signature(data: bytes, secret_key: bytes):
    signature = 'sha1=' + hmac.new(secret_key, msg=data, digestmod=hashlib.sha1).hexdigest()
    return signature

if __name__ == '__main__':
    app.run(host=conf.listen_ip, port=conf.listen_port, debug=True)
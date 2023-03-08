# -*- coding: utf-8 -*-

from flask import Flask, request, redirect, send_file, Response, stream_with_context, make_response
# Use gevent to speed up if needed.
'''
from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()
'''

import os
import requests
from hashlib import md5
from auth import *
from urllib.parse import unquote
from werkzeug.routing import BaseConverter

# 如果需要，可以设置代理
proxies = {"https": ""}

# 必须要填写的plus账号专属的_puid参数，如果你没有，可以问朋友要啊，又没有一定要自己的^_^
_puid = ""

# 支持多用户同时使用
password_list = [
    # 如果使用邮箱密码登录，只需填写`email_address`和`password`参数
    # 如果使用Chrome或Microsoft登录，需要`session_token`
    # 如果使用Chrome或Microsoft登录，又要开启账号密码登录的，需要重写user参数: user = md5(('your_email'+'your_password').encode()).hexdigest()
    {"email_address": "", "password": "", "session_token": None, "user": None},
]

# 如果需要，listen_url可以更改
# 如果更改此属性，则应还原resource目录
listen_url = "http://127.0.0.1"
listen_port = 8011

listen_url = listen_url + ":" + str(listen_port) if listen_url.count(".") > 1 else listen_url

# 如果需要，可以开启账号密码登录，设置: is_verify=True
is_verify = False

user_headers = {}
user_cookies = {}
session_json = ""
for i in password_list:
    email_address,password,session_token,user = i.values()
    cookie_dict = {"_puid":_puid}
    headers = {
        'authority': 'chat.openai.com',
        'accept': 'text/event-stream',
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://chat.openai.com',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
    }
    if email_address and password:
        Auth = Authenticator(email_address, password, proxies["https"])
        Auth.begin()
        access_token = Auth.get_access_token()
        session_token = Auth.get_session_token()
        cookie_dict["__Secure-next-auth.session-token"] = session_token
        cookie = '; '.join([f'{k}={v}' for k,v in cookie_dict.items()])
        headers["cookie"] = cookie
        headers["authorization"] = "Bearer " + access_token
        user =  md5((email_address+password).encode()).hexdigest() if not user else user
    else:
        cookie_dict["__Secure-next-auth.session-token"] = session_token
        cookie = '; '.join([f'{k}={v}' for k,v in cookie_dict.items()])
        headers["cookie"] = cookie
        headers["authorization"] = get_authorization(headers, cookie_dict, proxies)
    user_headers[user] = headers
    user_cookies[user] = cookie_dict

app = Flask(__name__)

# 自定义正则表达式转换器
class RegexConverter(BaseConverter):
    def __init__(self, map, *args):
        self.map = map
        self.regex = args[0]

# 绑定正则表达式转换器
app.url_map.converters['regex'] = RegexConverter

# 如果变更listen_url和listen_port，需要把这个目录删掉
resource_dir = './resource'
os.makedirs(resource_dir, exist_ok=True)

# 预加载登录和登录失败页面
with open('login.html', 'r', encoding='utf-8') as f:
    login_html = f.read()
with open('login_failed.html', 'r', encoding='utf-8') as f:
    login_failed_html = f.read()

# 登录认证
@app.route('/', methods=['GET', 'POST'])
def login():
    if not is_verify:
        return redirect('/chat',302)
    if request.cookies.get("accessToken") in user_headers:
        return redirect('/chat',302)
    if request.method =='GET':
        return login_html
    username = request.form['username']
    password = request.form['password']
    # user_id加密过程
    uid = md5((username+password).encode()).hexdigest()
    if uid in user_headers:
        resp = make_response(redirect('/chat',302))
        resp.set_cookie("accessToken", uid, max_age=604800)
        return resp
    else:
        return login_failed_html

# handles all HTTP request methods
@app.route('/<path:uri>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'TRACE', 'CONNECT', 'PATCH'])
def index(uri):
    # authentication cookie
    if is_verify and request.cookies.get("accessToken") not in user_headers:
        return redirect("/", 302)
    # signout
    if 'auth/signout' in uri:
        resp = make_response('{"url":"/"}'.encode())
        resp.delete_cookie("accessToken")
        return resp
    param = '&'.join([f'{i}={j}' for i,j in request.args.items()])
    url = f"https://chat.openai.com/{uri}?{param}" if param else f"https://chat.openai.com/{uri}"
    uid = request.cookies.get("accessToken")
    headers = user_headers[uid]
    cookie_dict = user_cookies[uid]
    # 如果请求是静态资源，则从本地获取，否则从远程获取
    if any(x in url for x in ('.jpg', '.png', '.ico', '.woff', '.otf', '.css', '.js')) and '.json' not in url:
        ext = url.split('.')[-1]
        if "?" in ext:
            ext = ext.split("?")[0]
        if "&" in ext:
            ext = ext.split("&")[0]
        filename = md5(url.encode('utf-8')).hexdigest()
        filepath = os.path.join(resource_dir, ext, f'{filename}.{ext}')
        if os.path.isfile(filepath):
            return send_file(filepath)
        else:
            r = requests.get(url, headers=headers, cookies=cookie_dict, data=request.data, proxies=proxies)
            if '.js' in url or '.css' in url:
                content = r.content.replace(b'https://chat.openai.com', listen_url.encode())
            else:
                content = r.content
            with open(filepath, 'wb') as f:
                f.write(content)
            return send_file(filepath)
    # 缓存页面 html
    elif '/backend' not in url and '/cdn-cgi' not in url and '.' not in url:
        filename = md5(url.encode('utf-8')).hexdigest()
        filepath = os.path.join(resource_dir, f'{filename}')
        if os.path.isfile(filepath):
            return send_file(filepath)
        else:
            r = requests.get(url, headers=headers, cookies=cookie_dict, data=request.data, proxies=proxies)
            content = r.content.replace(b'https://chat.openai.com', listen_url.encode())
            with open(filepath, 'wb') as f:
                f.write(content)
            return send_file(filepath)
    # 流传输
    elif 'conversation' in url:
        # If a live conversation is requested, the response is streamed
        r = requests.request(request.method, url, headers=headers, cookies=cookie_dict, data=request.data, proxies=proxies, stream=True)
        response = Response(stream_with_context(r.iter_content(chunk_size=1024)))
        response.headers['content-type'] = r.headers.get('content-type')
        return response
    # api请求
    else:
        r = requests.request(request.method, url, headers=headers, cookies=cookie_dict, data=request.data, proxies=proxies)
        return r.content.replace(b'https://chat.openai.com', listen_url.encode())

if __name__ == "__main__":
    host = '0.0.0.0' if '127.0.0.1' not in listen_url else '127.0.0.1'
    app.run(host=host, port=listen_port, threaded=True)
    # WSGIServer((host, listen_port), app).serve_forever()
    # 在浏览器打开: http://127.0.0.1:8011/chat
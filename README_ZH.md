# chatgpt-proxy-web

Flask 反向代理 ChatGPT 网站 chat.openai.com/chat。


[中文](https://github.com/cooolr/chatgpt-proxy-web/blob/main/README_ZH.md) | [English](https://github.com/cooolr/chatgpt-proxy-web/blob/main/README.md)

## 准备

您应该登录 [ChatGPT 网站](https://chat.openai.com/chat)，找到名为 `_puid` 的 cookie，然后复制值。

**该项目严重依赖于专用于 Plus 的 `_puid` 参数。 没有它，就无法绕过 CloudFlare。**

修改 `config.py` 来设置配置

``` python
# 如果更改了此属性，需要手动删除资源目录
listen_url = "http://127.0.0.1"
listen_port = 8011

# 开启页面的账号密码认证
is_verify = False

# 代理配置，http或socks5都可以
proxies = {"https": ""}

# Plus专属Cookie参数，如果没有，找朋友蹭一个
puid = ""

'''
1. 如果使用邮箱密码登录，则只需要填写email_address和password这两个参数
2. 如果使用Chrome或Microsoft登录，则只需要填写session_token这一个参数
3. 如果使用Chrome或Microsoft登录，并且同时开启了账号密码认证，则需要重写user参数
   user = md5(('your_email' + 'your_password').encode()).hexdigest()
'''

password_list = [
    {"email_address": "", "password": "", "session_token": None, "user": None},
]
```

## 安装依赖

``` bash
pip install -r requirements.txt
```

## 快速开始

``` bash
python3 main.py
```

浏览器打开链接：[http://127.0.0.1:8011/chat](http://127.0.0.1:8011/chat)

**需要使用域名访问的朋友，可以参考我的配置**

`config.py`
``` python
listen_url = "https://cooolr.online"
listen_port = 8011
```

`nginx.conf`
```plain text
server {
    location / {
        proxy_pass http://127.0.0.1:8011;
    }
}
```

## 注意

1. 只能用于Plus会员账号，免费账号不带_puid参数会有CF验证
2. 自动登录部分 `auth.py` ,感谢[https://github.com/acheong08/OpenAIAuth](https://github.com/acheong08/OpenAIAuth)

## 效果图
![登录](https://github.com/cooolr/chatgpt_plus_proxy_website/blob/main/static_files/login.png)
![聊天](https://github.com/cooolr/chatgpt_plus_proxy_website/blob/main/static_files/chat.png)

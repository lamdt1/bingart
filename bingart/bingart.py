import requests
import re
import time
import rookiepy
from urllib.parse import urlencode

class AuthCookieError(Exception):
    pass

class PromptRejectedError(Exception):
    pass

class BingArt:
    def __init__(self, auth_cookie_U=None, auth_cookie_KievRPSSecAuth=None, auto=False):
        self.session = requests.Session()
        self.base_url = 'https://www.bing.com/images/create'

        if auto:
            self.auth_cookie_U, self.auth_cookie_KievRPSSecAuth = self.get_auth_cookies()
        else:
            self.auth_cookie_U = auth_cookie_U
            self.auth_cookie_KievRPSSecAuth = auth_cookie_KievRPSSecAuth

        self.headers = self._prepare_headers()

    def scan_cookies(self, cookies):
        auth_cookie_U = auth_cookie_KievRPSSecAuth = None
        for cookie in cookies:
            if cookie['domain'] == '.bing.com':
                if cookie['name'] == '_U':
                    auth_cookie_U = cookie['value']
                elif cookie['name'] == 'KievRPSSecAuth':
                    auth_cookie_KievRPSSecAuth = cookie['value']
        return auth_cookie_U, auth_cookie_KievRPSSecAuth

    def get_auth_cookies(self):
        known_browsers = [
            'arc', 'brave', 'chrome', 'chromium', 'edge', 'firefox',
            'librewolf', 'octo_browser', 'opera', 'opera_gx', 'vivaldi'
        ]

        for browser_name in known_browsers:
            try:
                browser_func = getattr(rookiepy, browser_name)
                cookies = browser_func()
                auth_cookie_U, auth_cookie_KievRPSSecAuth = self.scan_cookies(cookies)
                if auth_cookie_U:
                    return auth_cookie_U, auth_cookie_KievRPSSecAuth
            except Exception:
                continue

        raise AuthCookieError('Failed to fetch authentication cookies automatically.')

    def _prepare_headers(self):
        cookie_str = ''
        if self.auth_cookie_U:
            cookie_str += f'_U={self.auth_cookie_U};'
        if self.auth_cookie_KievRPSSecAuth:
            cookie_str += f' KievRPSSecAuth={self.auth_cookie_KievRPSSecAuth};'

        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': self.base_url,
            'Accept-Language': 'en-US,en;q=0.9',
            'Cookie': cookie_str
        }

    def _get_balance(self):
        response = self.session.get(self.base_url)
        try:
            coins = int(re.search(r'<div id="reward_c" data-tb="(\d+)"', response.text).group(1))
        except AttributeError:
            raise AuthCookieError('Auth cookie failed!')
        return coins

    def _fetch_images(self, encoded_query, ID, IG):
        images = []
        while True:
            response = self.session.get(f'{self.base_url}/async/results/{ID}?{encoded_query}&IG={IG}&IID=images.as'.replace('&amp;nfy=1', ''))
            if 'text/css' in response.text:
                src_urls = re.findall(r'src="([^"]+)"', response.text)
                for src_url in src_urls:
                    if '?' in src_url:
                        clean_url = src_url.split('?')[0] + '?pid=ImgGn'
                        images.append({'url': clean_url})
                return images
            time.sleep(5)

    def generate_images(self, query):
        encoded_query = urlencode({'q': query})
        self.session.headers.update(self.headers)
        coins = self._get_balance()
        rt = '4' if coins > 0 else '3'
        creation_url = f'{self.base_url}?{encoded_query}&rt={rt}&FORM=GENCRE'

        response = self.session.post(creation_url, data={'q': query})
        try:
            ID = re.search(';id=([^"]+)"', response.text).group(1)
            IG = re.search('IG:"([^"]+)"', response.text).group(1)
        except AttributeError:
            raise PromptRejectedError('Error! Your prompt has been rejected for ethical reasons.')

        images = self._fetch_images(encoded_query, ID, IG)
        return {'images': images, 'prompt': query}

    def close_session(self):
        self.session.close()
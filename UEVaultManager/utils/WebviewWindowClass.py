# coding=utf-8
"""
Implementation for:
- WebviewWindow: Window to handle the webview login.
- do_webview_login() : launch the webview login.
"""
import json
import logging
import os
import webbrowser

# noinspection PyPep8Naming
from UEVaultManager import __version__ as UEVM_version

logger = logging.getLogger('WebViewHelper')
webview_available = True

try:
    # Note: webview don't came with the obsolete webview package but with [pywebview](https://pywebview.flowrl.com/)
    import webview

    # silence logger
    webview.logger.setLevel(logging.FATAL)
    gui = webview.initialize()
    if gui and os.name == 'nt' and gui.renderer not in ('edgechromium', 'cef'):
        raise NotImplementedError(f'Renderer {gui.renderer} not supported on Windows.')
except Exception as error:
    logger.debug(f'Webview unavailable, disabling webview login. Try to run "pip install pywebview" (Exception: {error!r}).')
    webview_available = False

login_url = 'https://www.epicgames.com/id/login'
sid_url = 'https://www.epicgames.com/id/api/redirect?'
logout_url = f'https://www.epicgames.com/id/logout?productName=epic-games&redirectUrl={login_url}'
goodbye_url = 'https://laurentongaro.github.io/UEVaultManager/statics/goodbye/index.html'
window_js = '''
window.ue = {
    signinprompt: {
        requestexchangecodesignin: pywebview.api.set_exchange_code,
        registersignincompletecallback: pywebview.api.trigger_sid_exchange
    },
    common: {
        launchexternalurl: pywebview.api.open_url_external
    }
}
'''

get_sid_js = '''
function on_loaded() {
    pywebview.api.login_sid(this.responseText);
}

var sid_req = new XMLHttpRequest();
sid_req.addEventListener("load", on_loaded);
sid_req.open("GET", "/id/api/redirect?");
sid_req.send();
'''


class WebviewWindow:
    """
    WebviewWindow to handle EGS login using a webview.
    :param callback_sid: callback function to handle the SID login.
    :param callback_code: callback function to handle the exchange code.
    """

    def __init__(self, callback_sid, callback_code):
        self.callback_sid = callback_sid
        self.callback_code = callback_code
        self.window = None
        self.inject_js = True
        self.destroy_on_load = False
        self.callback_result = None

    @staticmethod
    def open_url_external(url: str) -> None:
        """
        Open the given url in the default browser.
        :param url: url to open.
        """
        webbrowser.open(url)

    def on_loaded(self) -> None:
        """
        Callback function called when the login page is loaded.
        """
        url = self.window.get_current_url()
        logger.debug(f'Loaded url: {url.partition("?")[0]}')

        if self.destroy_on_load:
            logger.info('Closing login window...')
            self.window.destroy()
            return

        # Inject JS so required window.ue stuff is available
        if self.inject_js:
            self.window.evaluate_js(window_js)

        if 'logout' in url and self.callback_sid:
            # prepare to close browser after logout redirect
            self.destroy_on_load = True
        elif 'logout' in url:
            self.inject_js = True

    def nop(self, *args, **kwargs) -> None:
        """
        No operation function.
        :param args: arguments.
        :param kwargs: keyword arguments.
        """
        return

    def set_exchange_code(self, exchange_code: str) -> None:
        """
        Callback function called when the exchange code is received.
        :param exchange_code: exchange code.
        """
        self.inject_js = False
        logger.debug('Got exchange code (stage 1)!')
        # The default Windows webview retains cookies, GTK/Qt do not. Therefore, we can
        # skip logging out on those platforms and directly use the exchange code we're given.
        # On Windows we have to do a little dance with the SID to create a session that
        # remains valid after logging out in the embedded browser.
        #  Update: Epic broke SID login, we'll also do this on Windows now
        # if self.window.gui.renderer in ('gtkwebkit2', 'qtwebengine', 'qtwebkit'):
        self.destroy_on_load = True
        try:
            self.callback_result = self.callback_code(exchange_code)
        except Exception as _error:
            logger.error(f'Logging in via exchange-code failed with {_error!r}')
        finally:
            # We can not destroy the browser from here,
            # so we'll load a small goodbye site first.
            self.window.load_url(goodbye_url)

    def trigger_sid_exchange(self) -> None:
        """
        Trigger the SID exchange.
        """
        # check if code-based login hasn't already set the destroying flag
        if not self.destroy_on_load:
            logger.debug('Injecting SID JS')
            # inject JS to get SID API response and call our API
            self.window.evaluate_js(get_sid_js)

    def login_sid(self, sid_json: str) -> None:
        """
        Login with the given SID.
        :param sid_json: sID json.
        """
        # Try SID login, then log out
        try:
            j = json.loads(sid_json)
            sid = j['sid']
            logger.debug(f'Got SID (stage 2)! Executing sid login callback...')
            exchange_code = self.callback_sid(sid)
            if exchange_code:
                self.callback_result = self.callback_code(exchange_code)
        except Exception as _error:
            logger.error(f'SID log in failed with {_error!r}')
        finally:
            logger.debug('Starting browser logout...')
            self.window.load_url(logout_url)


def do_webview_login(callback_sid=None, callback_code=None, user_agent=None) -> None:
    """
    Open a webview window to log in to Epic Games.
    :param callback_sid: callback function to handle the SID login.
    :param callback_code: callback function to handle the exchange code.
    :param user_agent: user agent to use.
    """
    api = WebviewWindow(callback_sid=callback_sid, callback_code=callback_code)
    url = login_url

    if os.name == 'nt':
        # On Windows we open the logout URL first to invalidate the current cookies (if any).
        # Additionally, we have to disable JS injection for the first load, as otherwise the user
        # will get an error for some reason.
        url = logout_url
        api.inject_js = False

    logger.info('Opening Epic Games login window...')
    # Open logout URL first to remove existing cookies, then redirect to log in.
    window = webview.create_window(
        f'UEVaultManager {UEVM_version} - Epic Games Account Login', url=url, width=768, height=1024, js_api=api, on_top=True
    )
    api.window = window
    window.events.loaded += api.on_loaded

    try:
        webview.start(user_agent=user_agent)
    except Exception as we:
        logger.error(
            f'Running webview failed with {we!r}. If this error persists try the manual '
            f'login process by adding --disable-webview to your command line.'
        )
        return None

    if api.callback_result is None:
        logger.error('Login aborted by user.')

    return api.callback_result

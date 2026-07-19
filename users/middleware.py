"""
Logs a user out after IDLE_TIMEOUT_SECONDS of inactivity, checked server-side
on every request. This is the reliable piece of session expiry — unlike
SESSION_EXPIRE_AT_BROWSER_CLOSE, it doesn't depend on the browser actually
closing (some browsers restore sessions on relaunch and ignore that setting).

Add to MIDDLEWARE, after AuthenticationMiddleware and MessageMiddleware
(see README for exact placement).
"""
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout


class IdleTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_seconds = getattr(settings, 'IDLE_TIMEOUT_SECONDS', 30 * 60)

    def __call__(self, request):
        if request.user.is_authenticated:
            now = time.time()
            last_activity = request.session.get('last_activity')

            if last_activity is not None and (now - last_activity) > self.timeout_seconds:
                logout(request)  # cycles/flushes the session
                messages.info(request, "You were logged out due to inactivity. Please sign in again.")
            else:
                request.session['last_activity'] = now

        return self.get_response(request)
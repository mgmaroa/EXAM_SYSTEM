from django.contrib import messages
from django.shortcuts import redirect

def role_required(allowed_roles=[]):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.warning(
                request,
                "You don't have access to that page — here's your dashboard instead."
            )
            return redirect('dashboard_redirect')
        return _wrapped_view
    return decorator

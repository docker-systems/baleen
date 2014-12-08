from django.contrib.sites.models import Site
from django.conf import settings

def site_processor(request):
    """
    >>> site_processor(None)
    {'github_site_url': 'https://deploy.example.com/hub', 'site': <Site: example.com>}
    """
    return {
            'site': Site.objects.get_current(),
            'github_site_url': settings.GITHUB_HOOK_URL,
            }

def static_files(request):
    """
    >>> 'static' in static_files(None)
    True
    """
    return {
        'static': {
            'css': [
                'bootstrap/css/bootstrap.min.css',
                'google-code-prettify/prettify.css',
                'css/styles.css',
                'css/ui-lightness/jquery-ui-1.9.2.custom.min.css',
            ],
            'js': [
                'js/jquery-1.8.3.min.js',
                'js/jquery-ui-1.9.2.custom.min.js',
                'bootstrap/js/bootstrap.min.js',
                'js/underscore-min.js',
                'js/backbone-min.js',
                'js/moment-1.7.2.min.js',
                'js/testviewer.js',
                'js/project.js',
                'google-code-prettify/prettify.js',
            ],
        }
    }

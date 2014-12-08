SITE_URL = 'https://deploy.example.com'
SECRET_KEY = 'xxxxxx*&^#*@$&T@#%GI'
GITHUB_HOOK_URL = SITE_URL + '/hub'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

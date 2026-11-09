from settings.conf import config


def environment_callback(request):
    environment = config("BLOG_ENV_ID", default="local").lower()

    if environment == "production":
        return ["Production", "danger"]

    return ["Local", "warning"]
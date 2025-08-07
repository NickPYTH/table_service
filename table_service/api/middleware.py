from django.utils.deprecation import MiddlewareMixin


class RemoteUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        pass
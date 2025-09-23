# main/middleware.py
from django.utils.deprecation import MiddlewareMixin


class CookiesConsentMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Добавляем информацию о согласии в контекст запроса
        cookies_decision = request.COOKIES.get('cookies_decision')
        request.cookies_accepted = cookies_decision == 'accepted'

    def process_response(self, request, response):
        # Можно добавить логику для установки cookies на стороне сервера
        return response
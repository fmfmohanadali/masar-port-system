import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('core')


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        custom_response = {
            'success': False,
            'status_code': response.status_code,
            'errors': response.data,
        }
        if response.status_code == 400:
            custom_response['message'] = 'بيانات غير صالحة'
        elif response.status_code == 401:
            custom_response['message'] = 'يرجى تسجيل الدخول'
        elif response.status_code == 403:
            custom_response['message'] = 'ليس لديك صلاحية للوصول'
        elif response.status_code == 404:
            custom_response['message'] = 'العنصر غير موجود'
        elif response.status_code == 429:
            custom_response['message'] = 'طلبات كثيرة جداً، يرجى الانتظار'
        else:
            custom_response['message'] = 'حدث خطأ'
        response.data = custom_response
    else:
        logger.exception(f"Unhandled exception: {exc}")
        response = Response(
            {'success': False, 'status_code': 500, 'message': 'حدث خطأ داخلي', 'errors': {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response

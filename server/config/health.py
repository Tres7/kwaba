from django.db import connection
from django.http import JsonResponse


def health(request):
    """Health probe (Render, smoke test): the application responds and the database is reachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'error', 'database': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})

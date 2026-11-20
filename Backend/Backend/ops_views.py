import hmac

from django.conf import settings
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from Backend.alert_jobs import run_alert_check


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    """Lets the host (and an uptime monitor) check that the app is running."""
    return Response({'status': 'ok'})


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def check_alerts_job(request):
    """Runs the daily alert check. A scheduler calls this with:  Authorization: Bearer <CRON_SECRET>."""
    secret = settings.CRON_SECRET
    if not secret:
        return Response({'detail': 'Not found.'}, status=404)  # switched off: pretend the URL does not exist
    supplied = request.headers.get('Authorization', '')
    if not hmac.compare_digest(supplied.encode(), f'Bearer {secret}'.encode()):
        return Response({'detail': 'Forbidden.'}, status=403)
    result = run_alert_check()
    return Response({'detail': f"Checked {result['checked']} users: {result['new_alerts']} new alerts, "
                               f"{result['emailed']} emailed.", **result})
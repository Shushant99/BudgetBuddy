import logging

from django.core.cache import cache
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from Backend.emails import is_configured, send_test_email
from Backend.models import Profile

logger = logging.getLogger(__name__)


class EmailSettingsSerializer(serializers.Serializer):
    email_alerts = serializers.BooleanField(required=False)
    email_transactions = serializers.BooleanField(required=False)


def payload(user, profile):
    return {
        'email': user.email,
        'email_alerts': profile.email_alerts,
        'email_transactions': profile.email_transactions,
        'configured': is_configured(),  # False: the server only prints emails in its terminal
    }


@api_view(['GET', 'PATCH'])
def email_settings(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'PATCH':
        serializer = EmailSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(profile, field, value)
        profile.save(update_fields=[*serializer.validated_data, 'updated_at'])
    return Response(payload(request.user, profile))


@api_view(['POST'])
def email_test(request):
    """Send a sample email so the user (or whoever sets up the server) can check it all works."""
    if not request.user.email:
        return Response({'detail': 'Your account has no email address.'}, status=400)
    if not cache.add(f'test-email:{request.user.pk}', 1, timeout=30):
        return Response({'detail': 'Please wait a few seconds before sending another test email.'}, status=429)
    try:
        send_test_email(request.user)
    except Exception:
        logger.exception('Test email to user %s failed', request.user.pk)
        cache.delete(f'test-email:{request.user.pk}')
        return Response(
            {'detail': 'The email could not be sent. Check the EMAIL_ settings in Backend/.env and the server log.'},
            status=502,
        )
    if not is_configured():
        return Response({
            'detail': 'Email sending is not set up on the server yet, so the test email was printed in the '
                      'server terminal instead of being delivered. See the EMAIL_ settings in Backend/.env.',
            'delivered': False,
        })
    return Response({'detail': f'Test email sent to {request.user.email}.', 'delivered': True})
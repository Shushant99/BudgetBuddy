from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from Backend.models import Notification
from Backend.notifications import sync_time_based_alerts


def visible(user):
    return Notification.objects.filter(user=user, is_dismissed=False)


def serialize(n):
    return {
        'id': n.id, 'kind': n.kind, 'level': n.level, 'title': n.title, 'message': n.message,
        'link': n.link, 'is_read': n.is_read, 'created_at': n.created_at.isoformat(),
    }


def dismiss(queryset):
    """Delete notifications. Ones that carry a dedupe_key are only hidden so the alert is not repeated."""
    queryset.filter(dedupe_key__isnull=True).delete()
    queryset.filter(dedupe_key__isnull=False).update(is_dismissed=True, is_read=True)


@api_view(['GET', 'DELETE'])
def notification_list(request):
    if request.method == 'DELETE':
        dismiss(visible(request.user))
        return Response(status=204)

    sync_time_based_alerts(request.user)
    items = visible(request.user)
    unread_count = items.filter(is_read=False).count()
    if request.query_params.get('filter') == 'unread':
        items = items.filter(is_read=False)
    try:
        limit = min(max(int(request.query_params.get('limit', 50)), 1), 200)
    except ValueError:
        limit = 50
    return Response({'unread_count': unread_count, 'results': [serialize(n) for n in items[:limit]]})


@api_view(['POST'])
def notifications_read_all(request):
    updated = visible(request.user).filter(is_read=False).update(is_read=True, read_at=timezone.now())
    return Response({'updated': updated})


@api_view(['POST'])
def notification_read(request, notification_id):
    n = get_object_or_404(visible(request.user), pk=notification_id)
    if not n.is_read:
        n.is_read = True
        n.read_at = timezone.now()
        n.save(update_fields=['is_read', 'read_at'])
    return Response(serialize(n))


@api_view(['DELETE'])
def notification_delete(request, notification_id):
    n = get_object_or_404(visible(request.user), pk=notification_id)
    dismiss(Notification.objects.filter(pk=n.pk))
    return Response(status=204)
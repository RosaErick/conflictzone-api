"""DRF serializers: validate query params at the boundary, shape responses.

Query serializers return 400 on bad input (never silently ignore it). The
response serializer pins the exact field contract the frontend already consumes.
"""
from rest_framework import serializers


class OccurrenceQuerySerializer(serializers.Serializer):
    initialdate = serializers.DateField(required=False)
    finaldate = serializers.DateField(required=False)
    # `type` may repeat (multi-select); DRF reads getlist() from the QueryDict.
    type = serializers.ListField(child=serializers.CharField(), required=False)
    mainReason = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    policePresent = serializers.BooleanField(required=False, allow_null=True)
    victimStatus = serializers.ChoiceField(
        choices=['fatalities', 'injuries', 'none', 'all'], required=False
    )

    def validate(self, attrs):
        if (a := attrs.get('initialdate')) and (b := attrs.get('finaldate')) and a > b:
            raise serializers.ValidationError('initialdate must be on or before finaldate')
        return attrs


class PaginationQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    # Hard upper bound: list endpoints are never unbounded.
    take = serializers.IntegerField(required=False, min_value=1, max_value=5000, default=100)


class OccurrenceSerializer(serializers.Serializer):
    id = serializers.UUIDField(source='external_id')
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    address = serializers.CharField()
    date = serializers.DateTimeField(source='occurred_at')
    type = serializers.CharField(source='main_reason')
    fatalities = serializers.IntegerField()
    injuries = serializers.IntegerField()
    policePresent = serializers.BooleanField(source='police_present')
    neighborhood = serializers.CharField()
    city = serializers.CharField()
    weight = serializers.FloatField()

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lng(self, obj):
        return obj.location.x if obj.location else None

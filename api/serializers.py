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
    # `minLng,minLat,maxLng,maxLat` — parsed into a float tuple (the order
    # Polygon.from_bbox expects). Lets the map fetch only the current viewport.
    bbox = serializers.CharField(required=False)

    def validate_bbox(self, value):
        parts = value.split(',')
        if len(parts) != 4:
            raise serializers.ValidationError(
                'bbox must be 4 comma-separated numbers: minLng,minLat,maxLng,maxLat'
            )
        try:
            min_lng, min_lat, max_lng, max_lat = (float(p) for p in parts)
        except ValueError:
            raise serializers.ValidationError('bbox values must be numbers') from None
        if not (min_lng < max_lng and min_lat < max_lat):
            raise serializers.ValidationError('bbox needs minLng < maxLng and minLat < maxLat')
        if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180):
            raise serializers.ValidationError('bbox longitudes must be in [-180, 180]')
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise serializers.ValidationError('bbox latitudes must be in [-90, 90]')
        return (min_lng, min_lat, max_lng, max_lat)

    def validate(self, attrs):
        if (a := attrs.get('initialdate')) and (b := attrs.get('finaldate')) and a > b:
            raise serializers.ValidationError('initialdate must be on or before finaldate')
        return attrs


class DensityQuerySerializer(OccurrenceQuerySerializer):
    """Common filters + bbox (inherited) plus the grid cell size."""

    # Cell side in degrees (~0.005 ≈ 500 m at RJ). Clamped to keep the grid sane.
    cell = serializers.FloatField(required=False, min_value=0.001, max_value=0.05, default=0.005)


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

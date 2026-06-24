"""Serializers DRF: validam os query params na fronteira e moldam a resposta.

Os serializers de query retornam 400 em input inválido (nunca ignoram em silêncio).
O serializer de resposta fixa o contrato de campos que o frontend consome.
"""
from rest_framework import serializers


class OccurrenceQuerySerializer(serializers.Serializer):
    initialdate = serializers.DateField(required=False)
    finaldate = serializers.DateField(required=False)
    # `type` pode repetir (multi-select); o DRF lê getlist() do QueryDict.
    type = serializers.ListField(child=serializers.CharField(), required=False)
    mainReason = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    policePresent = serializers.BooleanField(required=False, allow_null=True)
    victimStatus = serializers.ChoiceField(
        choices=['fatalities', 'injuries', 'none', 'all'], required=False
    )
    # `minLng,minLat,maxLng,maxLat` — vira tupla de floats (ordem que
    # Polygon.from_bbox espera). Deixa o mapa buscar só o viewport atual.
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
    """Filtros comuns + bbox (herdados) mais o tamanho da célula do grid."""

    # Lado da célula em graus (~0.005 ≈ 500 m no RJ). Limitado p/ manter o grid sano.
    cell = serializers.FloatField(required=False, min_value=0.001, max_value=0.05, default=0.005)


class PaginationQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    # Teto rígido: endpoints de lista nunca são ilimitados.
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

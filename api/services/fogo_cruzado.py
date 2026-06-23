import re
import json
import requests
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from api.models import Occurrence
from django.core.serializers.json import DjangoJSONEncoder
from dateutil import parser


# Cache keys / TTLs
TOKEN_CACHE_KEY = 'fogo_cruzado_token'
OCCURRENCES_TTL = 300  # seconds the fetched dataset stays cached




class FogoCruzadoService:
    @staticmethod
    def count_fatalities(victims):
        """Count victims with 'Dead' situation status."""
        if not victims:
            return 0
        return sum(1 for v in victims if v.get('situation') == 'Dead')

    @staticmethod
    def count_injuries(victims):
        """Count victims with 'Injured' situation status."""
        if not victims:
            return 0
        return sum(1 for v in victims if v.get('situation') == 'Injured')

    @staticmethod
    def get_occurrence_type(context_info):
        """Extract occurrence type from contextInfo.mainReason.name."""
        if not context_info:
            return None
        return context_info.get('mainReason', {}).get('name')

    @staticmethod
    def get_token(force_refresh=False):
        """Return a valid access token, reusing a cached one until it expires.

        The Fogo Cruzado login endpoint rate-limits aggressively (429), so we
        log in only once per token lifetime instead of on every request.
        """
        if not force_refresh:
            cached = cache.get(TOKEN_CACHE_KEY)
            if cached:
                return cached

        url = "https://api-service.fogocruzado.org.br/api/v2/auth/login"
        credentials = {
            "email": settings.FOGO_CRUZADO_EMAIL,
            "password": settings.FOGO_CRUZADO_PASSWORD
        }
        response = requests.post(url, json=credentials, timeout=10)
        response.raise_for_status()
        data = response.json().get('data', {})
        token = data.get('accessToken')
        expires_in = data.get('expiresIn', 3600)
        # Cache a bit short of the real expiry to avoid using a token mid-rotation.
        cache.set(TOKEN_CACHE_KEY, token, timeout=max(expires_in - 60, 60))
        return token

    # City ID mapping for Rio de Janeiro metropolitan area
    CITY_IDS = {
        'rio de janeiro': 'd1bf56cc-6d85-4e6a-a5f5-0ab3f4074be3',
        'niteroi': 'a1234567-0000-0000-0000-000000000001',
        'sao goncalo': 'a1234567-0000-0000-0000-000000000002',
        'duque de caxias': 'a1234567-0000-0000-0000-000000000003',
        'nova iguacu': 'a1234567-0000-0000-0000-000000000004',
    }

    @staticmethod
    def fetch_data(token, filters=None):
        params = {
            'idState': 'b112ffbe-17b3-4ad0-8f2a-2038745d1d14',
            'take': 1000,
        }

        # Default to Rio de Janeiro if no city specified
        city_id = 'd1bf56cc-6d85-4e6a-a5f5-0ab3f4074be3'

        if filters:
            if 'initialdate' in filters and filters['initialdate']:
                params['initialdate'] = filters['initialdate']
            if 'finaldate' in filters and filters['finaldate']:
                params['finaldate'] = filters['finaldate']
            if 'typeOccurrence' in filters and filters['typeOccurrence']:
                params['typeOccurrence'] = filters['typeOccurrence']
            if 'city' in filters and filters['city']:
                city_name = filters['city'].lower()
                city_id = FogoCruzadoService.CITY_IDS.get(city_name, city_id)

        params['idCities[]'] = city_id

        # Reuse a recently fetched dataset: a dashboard hits several endpoints
        # at once, all asking for the same data. Cache by the actual params.
        cache_key = 'fogo_cruzado_occ:' + json.dumps(params, sort_keys=True)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        url = "https://api-service.fogocruzado.org.br/api/v2/occurrences"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()['data']
        print("length of the response:", len(data))
        cache.set(cache_key, data, timeout=OCCURRENCES_TTL)
        return data
    
    
    
    @staticmethod
    def calculate_weight(occurrence):
        weight = 4
        
        weight += len(occurrence.get('victims', [])) * 20
        
  
        if occurrence.get('policeAction', False) and occurrence.get('agentPresence', False):
            weight += 15
            
        return weight
    
    @staticmethod
    def validate_coordinate(value, is_latitude=True):
        try:
            cleaned_value = re.sub(r'[^\d.-]', '', value.strip())
            
            if re.match(r'^-?\d+(?:\.\d+)?$', cleaned_value) is None:
                raise ValueError(f"Invalid coordinate format: {value}")

            coord = float(cleaned_value)
            if is_latitude and -90 <= coord <= 90:  
                return coord
            elif not is_latitude and -180 <= coord <= 180:  
                return coord
            else:
                raise ValueError(f"Coordinate out of range: {value}")
        except ValueError as e:
            print(e)  
            return None

        
    @staticmethod
    def process_data(raw_data, filters=None):
        processed_data = []
        for item in raw_data:
         
            if filters and 'mainReason' in filters and filters['mainReason']:
                main_reason_filter = filters['mainReason']
                main_reason = item.get('contextInfo', {}).get('mainReason', {}).get('name', '')
                if main_reason_filter is not None and main_reason != main_reason_filter:
                    continue

            # Filter by police presence
            if filters and 'policePresent' in filters and filters['policePresent'] is not None:
                police_present = filters['policePresent']
                has_police = item.get('policeAction', False) or item.get('agentPresence', False)
                if police_present and not has_police:
                    continue
                if not police_present and has_police:
                    continue

            # Filter by type (mainReason.name)
            if filters and 'type' in filters and filters['type']:
                type_filter = filters['type']
                item_type = item.get('contextInfo', {}).get('mainReason', {}).get('name', '')
                if item_type != type_filter:
                    continue

            # Filter by victimStatus
            victims = item.get('victims', [])
            fatalities = sum(1 for v in victims if v.get('situation') == 'Dead')
            injuries = sum(1 for v in victims if v.get('situation') == 'Injured')

            if filters and 'victimStatus' in filters and filters['victimStatus']:
                status = filters['victimStatus']
                if status == 'fatalities' and fatalities == 0:
                    continue
                elif status == 'injuries' and injuries == 0:
                    continue
                elif status == 'none' and (fatalities > 0 or injuries > 0):
                    continue  
            
           
           
            latitude = FogoCruzadoService.validate_coordinate(item.get('latitude', '0'))
            longitude = FogoCruzadoService.validate_coordinate(item.get('longitude', '0'))

            weight = FogoCruzadoService.calculate_weight(item)
            context_info = item.get('contextInfo', {})
            police_action = item.get('policeAction', False)
            agent_presence = item.get('agentPresence', False)

            # Extract flattened values
            neighborhood_obj = item.get('neighborhood', {})
            city_obj = item.get('city', {})
            neighborhood_name = neighborhood_obj.get('name', '') if isinstance(neighborhood_obj, dict) else ''
            city_name = city_obj.get('name', '') if isinstance(city_obj, dict) else ''

            occurrence = Occurrence(
                occurrence_id=item['id'],
                latitude=latitude,
                longitude=longitude,
                address=item.get('address', ''),
                date=parser.isoparse(item.get('date', '1900-01-01T00:00:00.000Z')),
                police_action=police_action,
                agent_presence=agent_presence,
                context_info=context_info,
                victims=victims,
                weight=weight,
                neighborhood=neighborhood_obj,
                city=city_obj,
            )

            # Add computed fields as dynamic attributes
            occurrence.occurrence_type = FogoCruzadoService.get_occurrence_type(context_info)
            occurrence.fatalities = fatalities
            occurrence.injuries = injuries
            occurrence.police_present = police_action or agent_presence
            occurrence.neighborhood_name = neighborhood_name
            occurrence.city_name = city_name

            processed_data.append(occurrence)
        return processed_data
  

    @staticmethod
    def save_data(processed_data):
        for data in processed_data:
           
            print("Saving Occurrence - Context Info:", data.context_info)
            print("Saving Occurrence - Victims:", data.victims)

            occurrence, created = Occurrence.objects.get_or_create(
                occurrence_id=data.occurrence_id,
                defaults={
                    'latitude': data.latitude,
                    'longitude': data.longitude,
                    'address': data.address,
                    'date': data.date,
                    'police_action': data.police_action,
                    'agent_presence': data.agent_presence,
                    'context_info': data.context_info,
                    'victims': data.victims,
                    'weight': data.weight,
                    'neighborhood': data.neighborhood,
                    'city': data.city,
                }
            )
            if not created:
                occurrence.latitude = data.latitude
                occurrence.longitude = data.longitude
               
                occurrence.save()

    @classmethod
    def update_occurrences(cls, filters=None):
        try:
            token = cls.get_token()
            try:
                raw_data = cls.fetch_data(token, filters=filters)
            except requests.exceptions.HTTPError as e:
                # Cached token may have been revoked server-side: refresh once.
                if e.response is not None and e.response.status_code == 401:
                    token = cls.get_token(force_refresh=True)
                    raw_data = cls.fetch_data(token, filters=filters)
                else:
                    raise
            if raw_data is None:
                print("raw_data is None")
                return []
            
            processed_data = cls.process_data(raw_data, filters=filters)
            if processed_data is None:
                print("processed_data is None")
                return []

            
            return processed_data
        except Exception as e:
            print(f"Error in update_occurrences: {str(e)}")
            return []

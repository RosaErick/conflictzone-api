import requests
from datetime import datetime
from django.conf import settings
from fogo_cruzado.models import Occurrence
from django.core.serializers.json import DjangoJSONEncoder



class FogoCruzadoService:
    @staticmethod
    def get_token():
        url = "https://api-service.fogocruzado.org.br/api/v2/auth/login"
        credentials = {
            "email": settings.FOGO_CRUZADO_EMAIL,
            "password": settings.FOGO_CRUZADO_PASSWORD
        }
        response = requests.post(url, json=credentials)
        response.raise_for_status()
        return response.json().get('data', {}).get('accessToken')

    @staticmethod
    def fetch_data(token, filters=None):
        params = {
            'idState': 'b112ffbe-17b3-4ad0-8f2a-2038745d1d14',
            'take': 5000,
        }
        
        if filters:
            if 'initialdate' in filters and filters['initialdate']:
                params['initialdate'] = filters['initialdate']
            if 'finaldate' in filters and filters['finaldate']:
                params['finaldate'] = filters['finaldate']

        
        
        url = "https://api-service.fogocruzado.org.br/api/v2/occurrences"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        
        print("url with params:", response.url)
        print(response.json()['data'])
        return response.json()['data']

    @staticmethod
    def process_data(raw_data, filters=None):
        processed_data = []
        for item in raw_data:
            print("filter:", filters)
            if filters and 'mainReason' in filters:
                main_reason_filter = filters['mainReason']
                main_reason = item.get('contextInfo', {}).get('mainReason', {}).get('name')
                if main_reason_filter and main_reason != main_reason_filter:
                    continue

            occurrence = Occurrence(
                occurrence_id=item['id'],
                latitude=float(item.get('latitude', 0)),
                longitude=float(item.get('longitude', 0)),
                address=item.get('address', ''),
                date=datetime.fromisoformat(item.get('date', '1900-01-01T00:00:00.000Z')),
                police_action=item.get('policeAction', False),
                agent_presence=item.get('agentPresence', False),
                context_info=item.get('contextInfo', {}),  
                victims=item.get('victims', [])           
            )
            processed_data.append(occurrence)
        return processed_data
  

    @staticmethod
    def save_data(processed_data):
        for data in processed_data:
            # Debugging: Print values before saving
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
                    'victims': data.victims
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
            raw_data = cls.fetch_data(token, filters=filters)
            if raw_data is None:
                print("raw_data is None")
                return []
            
            processed_data = cls.process_data(raw_data, filters=filters)
            if processed_data is None:
                print("processed_data is None")
                return []

            print("Processed Data:", processed_data)
            return processed_data
        except Exception as e:
            print(f"Error in update_occurrences: {str(e)}")
            return []

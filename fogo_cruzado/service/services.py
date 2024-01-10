import requests
from datetime import datetime
from django.conf import settings
from fogo_cruzado.models import Occurrence

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
    def fetch_data(token):
        params = {
            'agentPresence': 'true',
            'idState': 'b112ffbe-17b3-4ad0-8f2a-2038745d1d14',
            'policeAction': 'true',
            'page': '1',
            'take': '1000'  # Adjust the number of records as needed
        }
        url = "https://api-service.fogocruzado.org.br/api/v2/occurrences"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        print(response.json()['data'])
        return response.json()['data']

    @staticmethod
    def process_data(raw_data):
        processed_data = []
        for item in raw_data:
            # Processing and validation logic here
            occurrence = Occurrence(
                occurrence_id=item['id'],
                latitude=float(item.get('latitude', 0)),  # Defaulting to 0 if not available
                longitude=float(item.get('longitude', 0)),
                address=item.get('address', ''),
                date=datetime.fromisoformat(item.get('date', '1900-01-01T00:00:00.000Z')),
                police_action=item.get('policeAction', False),
                agent_presence=item.get('agentPresence', False)
            )
            processed_data.append(occurrence)
            
        print(processed_data)
        return processed_data

    @staticmethod
    def save_data(processed_data):
        for data in processed_data:
            occurrence, created = Occurrence.objects.get_or_create(
            occurrence_id=data.occurrence_id,
            defaults={
                'latitude': data.latitude,
                'longitude': data.longitude,
                'address': data.address,
                'date': data.date,
                'police_action': data.police_action,
                'agent_presence': data.agent_presence
            }
        )
        if not created:
        
            occurrence.latitude = data.latitude
            occurrence.longitude = data.longitude
            # ... update other fields if necessary
            occurrence.save()

    @classmethod
    def update_occurrences(cls):
        token = cls.get_token()
        raw_data = cls.fetch_data(token)
        processed_data = cls.process_data(raw_data)
        cls.save_data(processed_data)

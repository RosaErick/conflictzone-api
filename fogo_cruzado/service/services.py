import re 
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
            'take': 10000,
        }
        
        if filters:    
            if 'initialdate' in filters and filters['initialdate']:
                params['initialdate'] = filters['initialdate']
            if 'finaldate' in filters and filters['finaldate']:
                params['finaldate'] = filters['finaldate']
            if 'typeOccurrence' in filters and filters['typeOccurrence']:
                params['typeOccurrence'] = filters['typeOccurrence']   

       

        
       
        
        url = "https://api-service.fogocruzado.org.br/api/v2/occurrences"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        
        print("url with params:", response.url)
        

        
        print("length of the response:", len(response.json()['data']))
        
        return response.json()['data']
    
    
    
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
                    continue  # Skip this occurrence
            
           
           
            latitude = FogoCruzadoService.validate_coordinate(item.get('latitude', '0'))
            longitude = FogoCruzadoService.validate_coordinate(item.get('longitude', '0'))
            
            weight = FogoCruzadoService.calculate_weight(item)
                    
            occurrence = Occurrence(
                occurrence_id=item['id'],
                latitude=latitude,
                longitude=longitude,
                address=item.get('address', ''),
                date=datetime.fromisoformat(item.get('date', '1900-01-01T00:00:00.000Z')),
                police_action=item.get('policeAction', False),
                agent_presence=item.get('agentPresence', False),
                context_info=item.get('contextInfo', {}),  
                victims=item.get('victims', []),
                weight=weight,           
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
                    'victims': data.victims,
                    'weight': data.weight,
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

            
            return processed_data
        except Exception as e:
            print(f"Error in update_occurrences: {str(e)}")
            return []

from django.shortcuts import render
from django.http import HttpResponse
import requests
from django.conf import settings
from django.http import JsonResponse

def get_fogo_cruzado_token():
    url = "https://api-service.fogocruzado.org.br/api/v2/auth/login"
    credentials = {
        "email": settings.FOGO_CRUZADO_EMAIL,
        "password": settings.FOGO_CRUZADO_PASSWORD
    }
    response = requests.post(url, json=credentials)
    response.raise_for_status()  # This will raise an error for non-2xx responses
    print(response.json())
    return response.json().get('data', {}).get('accessToken')


def fetch_fogo_cruzado_occurrences():
    token = get_fogo_cruzado_token()
    if not token:
        raise ValueError("Failed to retrieve Fogo Cruzado token")

    print(token)
    # Filters for state and city of Rio de Janeiro, with agentPresence true
    params = {
         'agentPresence': 'true',
        'idState': 'b112ffbe-17b3-4ad0-8f2a-2038745d1d14',
    }
    url = "https://api-service.fogocruzado.org.br/api/v2/occurrences"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers, params=params)
    print("response", response)
    response.raise_for_status()

    
    return response.json()



def health_view(request):
    return HttpResponse("Health Check OK CARAJOOOOO")



def occurrences_view(request):
    try:
        occurrences = fetch_fogo_cruzado_occurrences()
        return JsonResponse(occurrences, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from .service.services import FogoCruzadoService

def health_view(request):
    return HttpResponse("Health Check OK CARAJOOOOO")


def occurrences_view(request):
    try:
        processed_data = FogoCruzadoService.update_occurrences()

        data = []
        for occurrence in processed_data:
            occurrence_dict = {
                'occurrence_id': occurrence.occurrence_id,
                'lat': occurrence.latitude,
                'lng': occurrence.longitude,
                'address': occurrence.address,
                'date': occurrence.date,
                'weight': 1, # TODO: Calculate weight based on 'police_action' and 'agent_presence
                'police_action': occurrence.police_action,
                'agent_presence': occurrence.agent_presence,
                'context_info': occurrence.context_info,  
                'victims': occurrence.victims            
            }
            data.append(occurrence_dict)

        return JsonResponse({'occurrences': data}, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from .service.services import FogoCruzadoService

def health_view(request):
    return HttpResponse("Health Check")


def occurrences_view(request):
    try:
       
        filters = {
            'initialdate': request.GET.get('initialdate'),
            'finaldate': request.GET.get('finaldate'),
            'mainReason': request.GET.get('mainReason'),
            'typeOccurrence': request.GET.get('typeOccurrence')
        }
        
        
        processed_data = FogoCruzadoService.update_occurrences(filters=filters)

        data = []
        for occurrence in processed_data:
            occurrence_dict = {
                'occurrence_id': occurrence.occurrence_id,
                'lat': occurrence.latitude,
                'lng': occurrence.longitude,
                'address': occurrence.address,
                'date': occurrence.date,
                'weight': occurrence.weight,  
                'police_action': occurrence.police_action,
                'agent_presence': occurrence.agent_presence,
                'context_info': occurrence.context_info,  
                'victims': occurrence.victims,
                'neighborhood': occurrence.neighborhood,
                'city': occurrence.city,            
            }
            data.append(occurrence_dict)  

        return JsonResponse({'occurrences': data}, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
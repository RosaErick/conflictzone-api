from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from .service.services import FogoCruzadoService
from .models import Occurrence
import json





def health_view(request):
    return HttpResponse("Health Check OK CARAJOOOOO")


def occurrences_view(request):
    try:
        processed_data = FogoCruzadoService.update_occurrences()

        data = []
        for occurrence in processed_data:
            occurrence_dict = {
                'occurrence_id': occurrence.occurrence_id,
                'latitude': occurrence.latitude,
                'longitude': occurrence.longitude,
                'address': occurrence.address,
                'date': occurrence.date,
                'police_action': occurrence.police_action,
                'agent_presence': occurrence.agent_presence,
                'context_info': occurrence.context_info,  # Already a JSON string
                'victims': occurrence.victims            # Already a JSON string
            }
            data.append(occurrence_dict)

        return JsonResponse({'occurrences': data}, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
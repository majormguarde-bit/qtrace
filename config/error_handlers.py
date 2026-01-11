from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)

def custom_page_not_found(request, exception):
    host = request.get_host()
    path = request.path
    tenant = getattr(request, 'tenant', 'None')
    schema = getattr(tenant, 'schema_name', 'None') if tenant != 'None' else 'None'
    
    logger.error(f"404 error: host={host}, path={path}, tenant={tenant}, schema={schema}")
    
    return render(request, '404.html', {
        'host': host,
        'path': path,
        'tenant': tenant,
        'schema': schema
    }, status=404)

def custom_server_error(request):
    host = request.get_host()
    path = request.path
    tenant = getattr(request, 'tenant', 'None')
    
    logger.error(f"500 error: host={host}, path={path}, tenant={tenant}")
    
    return render(request, '500.html', status=500)

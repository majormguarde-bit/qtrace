
import os

filepath = 'customers/views.py'
try:
    with open(filepath, 'rb') as f:
        lines = f.readlines()
    
    # Keep lines up to 2986 (which corresponds to index 2986 in 1-based line numbers, so index 2986 in 0-based list is line 2987. Wait.)
    # Read tool output line numbers start at 1.
    # Line 2987 is "@user_passes_test..."
    # So I want to keep lines 0 to 2986 (exclusive of 2987).
    # In python list slicing, lines[:2987] gives elements 0..2986.
    
    # Let's verify line 2987 content from the lines list to be sure.
    print(f"Line 2987 content: {lines[2987]}")
    
    # If it matches the corrupted function start, we are good.
    # Actually, let's just search for the line starting with "def superuser_position_create_api" and truncate before the decorator.
    
    cut_index = -1
    for i, line in enumerate(lines):
        if b'def superuser_position_create_api' in line:
            cut_index = i - 1 # The decorator is usually the line before
            break
            
    if cut_index != -1:
        print(f"Truncating at line {cut_index+1}")
        new_content = b''.join(lines[:cut_index])
        
        # Append the clean function
        new_function = """
@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_position_create_api(request):
    \"\"\"API endpoint для быстрого создания должности\"\"\"
    from task_templates.models import Position
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Название не может быть пустым'}, status=400)
    
    try:
        position, created = Position.objects.get_or_create(
            name__iexact=name,
            defaults={'name': name, 'is_active': True}
        )
        
        return JsonResponse({
            'success': True,
            'position': {
                'id': position.id,
                'name': position.name
            },
            'exists': not created
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
"""
        # Encode to utf-8
        new_content += new_function.encode('utf-8')
        
        with open(filepath, 'wb') as f:
            f.write(new_content)
        print("File fixed.")
    else:
        print("Could not find the function to replace.")

except Exception as e:
    print(f"Error: {e}")

from rest_framework import serializers
from .models import Task, TaskStage

class TaskStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStage
        fields = [
            'id', 'name', 'executor_role', 'planned_duration', 'actual_duration', 
            'status', 'reason_code', 'defect_criticality', 'damage_amount', 'order', 'is_completed'
        ]

class TaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    stages = TaskStageSerializer(many=True, read_only=True)
    lead_time = serializers.IntegerField(read_only=True)
    cycle_time = serializers.IntegerField(read_only=True)
    wait_time = serializers.IntegerField(read_only=True)
    efficiency_score = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'external_id', 'title', 'description', 'process_type', 
            'priority', 'control_object', 'source', 'status', 'status_display', 
            'is_completed', 'created_at', 'closed_at', 'stages', 
            'lead_time', 'cycle_time', 'wait_time', 'efficiency_score'
        ]

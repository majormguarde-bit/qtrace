from rest_framework import serializers
from .models import Task, TaskStage

class TaskStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStage
        fields = ['id', 'name', 'duration_minutes', 'order', 'is_completed']

class TaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    stages = TaskStageSerializer(many=True, read_only=True)
    total_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'status_display', 'is_completed', 'created_at', 'stages', 'total_duration']

    def get_total_duration(self, obj):
        return sum(stage.duration_minutes for stage in obj.stages.all())

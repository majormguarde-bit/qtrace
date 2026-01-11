from rest_framework import serializers
from .models import Media

class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ['id', 'title', 'file', 'task', 'recording_start', 'recording_end', 'uploaded_by', 'uploaded_at']
        read_only_fields = ('uploaded_by', 'uploaded_at')

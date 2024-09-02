from django.utils import timezone
from rest_framework import serializers

from .models import Board, CustomUser, JournalEntry, List, Task


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)


class ListSerializer(serializers.ModelSerializer):

    class Meta:
        model = List
        fields = ['id', 'name', 'board', 'position']
        read_only_fields = ['position']


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(many=True, read_only=True)
    assigned_to_ids = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), many=True, write_only=True)
    priority_display = serializers.CharField(source='get_priority_display',
                                             read_only=True)
    complexity_display = serializers.CharField(source='get_complexity_display',
                                               read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'due_date', 'priority',
            'priority_display', 'complexity', 'complexity_display', 'list',
            'assigned_to', 'assigned_to_ids', 'position', 'completed'
        ]
        read_only_fields = ['position']

    def create(self, validated_data):
        assigned_to_ids = validated_data.pop('assigned_to_ids', [])
        task = Task.objects.create(**validated_data)
        task.assigned_to.set(assigned_to_ids)
        return task

    def update(self, instance, validated_data):
        assigned_to_ids = validated_data.pop('assigned_to_ids', None)

        if assigned_to_ids is not None:
            instance.assigned_to.set(assigned_to_ids)

        return super().update(instance, validated_data)


class TaskDropdownSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = ['id', 'title']


class ListWithTasksSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = List
        fields = ['id', 'name', 'position', 'tasks']


class BoardSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ['id', 'name', 'members']


class BoardDetailSerializer(serializers.ModelSerializer):
    lists = ListWithTasksSerializer(many=True, read_only=True)
    members = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ['id', 'name', 'members', 'lists']


class JournalEntrySerializer(serializers.ModelSerializer):
    shared_with = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), many=True)
    mood_index = serializers.FloatField(read_only=True)
    task = TaskSerializer(read_only=True)
    task_id = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all(),
                                                 source='task',
                                                 write_only=True,
                                                 required=False,
                                                 allow_null=True)
    created_at = serializers.DateTimeField(required=False)

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'title', 'content', 'created_at', 'task', 'task_id',
            'valence', 'arousal', 'visibility', 'shared_with', 'mood_index'
        ]

    def validate(self, data):

        if (data.get('valence') is None) != (data.get('arousal') is None):
            raise serializers.ValidationError(
                "Both valence and arousal must be provided together or not at all."
            )
        return data

    def validate_created_at(self, value):
        if value is None:
            return timezone.now()
        if value > timezone.now():
            raise serializers.ValidationError(
                "Created at date cannot be in the future.")
        return value

    def validate_task(self, value):
        # logger.info(f"Validating task: {value}")
        if isinstance(value, dict):
            task_id = value.get('id')
            if task_id is not None:
                try:
                    return Task.objects.get(id=task_id)
                except Task.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Task with id {task_id} does not exist.")
            else:
                raise serializers.ValidationError(
                    "Invalid task object: missing 'id'.")
        elif isinstance(value, int):
            try:
                return Task.objects.get(id=value)
            except Task.DoesNotExist:
                raise serializers.ValidationError(
                    f"Task with id {value} does not exist.")
        elif value is None:
            return None
        else:
            raise serializers.ValidationError(f"Invalid task value: {value}")

    def create(self, validated_data):
        shared_with = validated_data.pop('shared_with', [])
        if 'created_at' not in validated_data:
            validated_data['created_at'] = timezone.now()
        journal_entry = JournalEntry.objects.create(**validated_data)
        journal_entry.shared_with.set(shared_with)
        return journal_entry

    def update(self, instance, validated_data):
        new_visibility = validated_data.get('visibility', instance.visibility)
        current_visibility = instance.visibility

        shared_with = validated_data.pop('shared_with', None)

        task_data = self.initial_data.get('task')
        if task_data is not None:
            task = self.validate_task(task_data)
            instance.task = task
        elif 'task' in self.initial_data:
            instance.task = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if current_visibility == 'shared' and new_visibility != 'shared':
            instance.shared_with.clear()

        if shared_with is not None and new_visibility == 'shared':
            instance.shared_with.set(shared_with)

        instance.save()
        return instance

from datetime import timedelta

from django.db.models import (Avg, Count, ExpressionWrapper, F, FloatField,
                              Func, Max, Min, Q)
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from api import serializers
from api.permissions import IsBoardMember

from .models import Board, CustomUser, JournalEntry, List, Task
from .serializers import (BoardDetailSerializer, BoardSerializer,
                          JournalEntrySerializer, ListSerializer,
                          TaskDropdownSerializer, TaskSerializer,
                          UserSerializer)


class Sqrt(Func):
    function = 'SQRT'
    arity = 1
    output_field = FloatField()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]


class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    pass


class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [permissions.IsAuthenticated, IsBoardMember]

    def get_queryset(self):
        return self.queryset.filter(members=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BoardDetailSerializer
        return BoardSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        board = serializer.instance
        board.members.add(request.user)

        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        board = self.get_object()
        username = request.data.get('username')
        try:
            user = CustomUser.objects.get(username=username)
            if user not in board.members.all():
                board.members.add(user)
                user_data = UserSerializer(user).data
                return Response({
                    'status': 'user added to board',
                    'user': user_data
                })
            return Response({'status': 'user already in board'}, status=400)
        except CustomUser.DoesNotExist:
            return Response({'status': 'user not found'}, status=404)


class ListViewSet(viewsets.ModelViewSet):
    queryset = List.objects.all()
    serializer_class = ListSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['board']
    ordering_fields = ['position']

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        list_obj = self.get_object()
        new_position = request.data.get('position')
        if new_position is not None:
            new_position = int(new_position)
            if new_position < 0:
                return Response({'status': 'invalid position'},
                                status=status.HTTP_400_BAD_REQUEST)

            old_position = list_obj.position

            if new_position != old_position:
                if new_position < old_position:
                    List.objects.filter(board=list_obj.board,
                                        position__gte=new_position,
                                        position__lt=old_position).update(
                                            position=F('position') + 1)
                else:
                    List.objects.filter(board=list_obj.board,
                                        position__gt=old_position,
                                        position__lte=new_position).update(
                                            position=F('position') - 1)

                list_obj.position = new_position
                list_obj.save()

            return Response({'status': 'list moved'})
        return Response({'status': 'invalid position'},
                        status=status.HTTP_400_BAD_REQUEST)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['list', 'assigned_to', 'priority', 'complexity']
    ordering_fields = ['position', 'due_date', 'priority']

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        task = self.get_object()
        new_position = request.data.get('position')
        new_list_id = request.data.get('list_id')
        if new_position is not None:
            new_position = int(new_position)
            if new_position < 0:
                return Response({'status': 'invalid position'},
                                status=status.HTTP_400_BAD_REQUEST)
            old_position = task.position
            old_list = task.list
            if new_list_id and int(new_list_id) != old_list.id:
                new_list = List.objects.get(id=new_list_id)
                Task.objects.filter(list=old_list,
                                    position__gt=old_position).update(
                                        position=F('position') - 1)
                Task.objects.filter(list=new_list,
                                    position__gte=new_position).update(
                                        position=F('position') + 1)
                task.list = new_list
            elif new_position != old_position:
                if new_position < old_position:
                    Task.objects.filter(list=task.list,
                                        position__gte=new_position,
                                        position__lt=old_position).update(
                                            position=F('position') + 1)
                else:
                    Task.objects.filter(list=task.list,
                                        position__gt=old_position,
                                        position__lte=new_position).update(
                                            position=F('position') - 1)
            task.position = new_position
            task.save()
            return Response({'status': 'task moved'})
        return Response({'status': 'invalid position'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        task = self.get_object()
        user = request.user
        task.assigned_to.add(user)
        return Response({'status': 'task assigned'})


class JournalEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user)

    def get_extended_queryset(self):
        user = self.request.user
        return JournalEntry.objects.filter(
            Q(user=user) | Q(visibility='public')
            | (Q(visibility='shared') & Q(shared_with=user)))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance,
                                         data=request.data,
                                         partial=partial)

        try:
            serializer.is_valid(raise_exception=True)
            updated_instance = serializer.save()
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": "An unexpected error occurred."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='mood-statistics')
    def mood_statistics(self, request):
        """
        Retrieve mood statistics for the last 30 days.

        Returns:
            Response: A list of dictionaries containing date and mood_index for each day.
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        journal_entries = self.get_queryset().filter(
            created_at__date__range=(start_date, end_date),
            valence__isnull=False,
            arousal__isnull=False).values('created_at__date').annotate(
                mood_index=Avg(
                    Sqrt(
                        ExpressionWrapper(F('valence')**2 + F('arousal')**2,
                                          output_field=FloatField()))
                )).order_by('created_at__date')

        data = [{
            'date': entry['created_at__date'].isoformat(),
            'mood_index': entry['mood_index']
        } for entry in journal_entries]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='heatmap-data')
    def heatmap_data(self, request):
        """
        Endpoint to retrieve data for generating a heatmap of mood indices
        based on task complexity and priority.
        """
        data = self.get_queryset().filter(
            task__isnull=False,
            valence__isnull=False, arousal__isnull=False).values(
                'task__complexity', 'task__priority').annotate(mood_index=Avg(
                    Sqrt(
                        ExpressionWrapper(
                            F('valence')**2 + F('arousal')**2,
                            output_field=FloatField())))).order_by(
                                'task__complexity', 'task__priority')

        heatmap_data = [{
            'complexity': item['task__complexity'],
            'priority': item['task__priority'],
            'mood_index': item['mood_index']
        } for item in data]
        return Response(heatmap_data)

    @action(detail=True, methods=['get'], url_path='task-mood-statistics')
    def task_mood_statistics(self, request, pk=None):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({"error": "Task not found."},
                            status=status.HTTP_404_NOT_FOUND)

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = self.get_extended_queryset().filter(task=task)

        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        data = queryset.filter(
            valence__isnull=False,
            arousal__isnull=False).values('created_at__date').annotate(
                avg_mood_index=Avg(
                    Sqrt(
                        ExpressionWrapper(F('valence')**2 + F('arousal')**2,
                                          output_field=FloatField()))),
                min_mood_index=Min(
                    Sqrt(
                        ExpressionWrapper(F('valence')**2 + F('arousal')**2,
                                          output_field=FloatField()))),
                max_mood_index=Max(
                    Sqrt(
                        ExpressionWrapper(F('valence')**2 + F('arousal')**2,
                                          output_field=FloatField()))),
                entry_count=Count('id')).order_by('created_at__date')
        # print(data)
        return Response(data)

    @action(detail=True, methods=['get'], url_path='task-mood-history')
    def task_mood_history(self, request, pk=None):
        """
        Retrieve mood history for a specific task.

        Args:
            pk (int): The primary key of the task.

        Returns:
            Response: A list of dictionaries containing mood entry details.
        """
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({"error": "Task not found."},
                            status=status.HTTP_404_NOT_FOUND)

        journal_entries = self.get_extended_queryset().filter(
            task=task).order_by('created_at')

        data = [{
            'date': entry.created_at.isoformat(),
            'mood_index': entry.mood_index,
            'title': entry.title,
            'content': entry.content,
            'visibility': entry.visibility,
            'user': entry.user.username
        } for entry in journal_entries]

        return Response(data)

    @action(detail=True, methods=['get'], url_path='project-overview')
    def project_overview(self, request, pk=None):
        """
        Retrieve a project-wide overview of mood statistics.

        Query Parameters:
            start_date (str): Optional. Start date for filtering (format: YYYY-MM-DD).
            end_date (str): Optional. End date for filtering (format: YYYY-MM-DD).

        Returns:
            Response: A list of dictionaries containing daily mood statistics.
        """
        try:
            board = Board.objects.get(pk=pk)
        except Board.DoesNotExist:
            return Response({"error": "Board not found."},
                            status=status.HTTP_404_NOT_FOUND)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = self.get_extended_queryset().filter(task__list__board=board)

        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        data = queryset.filter(
            valence__isnull=False,
            arousal__isnull=False).values('created_at__date').annotate(
                avg_mood_index=Avg(
                    Sqrt(
                        ExpressionWrapper(F('valence')**2 + F('arousal')**2,
                                          output_field=FloatField()))),
                min_mood_index=Min(
                    Sqrt(
                        ExpressionWrapper(F('valence')**2 + F('arousal')**2,
                                          output_field=FloatField()))),
                max_mood_index=Max(
                    Sqrt(
                        ExpressionWrapper(F('valence')**2 + F('arousal')**2,
                                          output_field=FloatField()))),
                entry_count=Count('id')).order_by('created_at__date')
        return Response(data)

    @action(detail=False, methods=['GET'], url_path='available-tasks')
    def available_tasks(self, request):
        """
            Retrieve all tasks that the user is assigned to and can be linked to a journal entry.
            """
        user_tasks = Task.objects.filter(assigned_to=request.user)
        serializer = TaskDropdownSerializer(user_tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'], url_path='shareable-users')
    def shareable_users(self, request):
        """
            Retrieve all users that are in the same boards as the current user.
            """
        user_boards = Board.objects.filter(members=request.user)
        shareable_users = CustomUser.objects.filter(
            boards__in=user_boards).exclude(id=request.user.id).distinct()
        serializer = UserSerializer(shareable_users, many=True)
        return Response(serializer.data)


class DashboardViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        user = request.user
        now = timezone.now()
        all_tasks = Task.objects.filter(assigned_to=user)

        uncompleted_tasks = all_tasks.filter(
            completed=False).order_by('due_date')
        uncompleted_tasks_data = list(
            uncompleted_tasks.values('id', 'title', 'due_date', 'completed',
                                     'priority', 'list__board__id'))

        for task in uncompleted_tasks_data:
            task['board_id'] = task.pop('list__board__id')

        data = {
            'total_tasks':
            all_tasks.count(),
            'completed_tasks':
            all_tasks.filter(completed=True).count(),
            'all_tasks':
            uncompleted_tasks_data,
            'tasks_completed_this_week':
            all_tasks.filter(completed=True,
                             completed_at__gte=now -
                             timedelta(days=7)).count(),
        }
        return Response(data)

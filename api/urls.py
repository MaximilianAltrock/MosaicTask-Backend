from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (BoardViewSet, CustomTokenRefreshView, DashboardViewSet,
                    JournalEntryViewSet, ListViewSet, LoginView, RegisterView,
                    TaskViewSet)

router = DefaultRouter()
router.register(r'boards', BoardViewSet)
router.register(r'lists', ListViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'journal-entries',
                JournalEntryViewSet,
                basename='journalentry')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/',
         CustomTokenRefreshView.as_view(),
         name='token_refresh'),
    path('lists/<int:pk>/move/',
         ListViewSet.as_view({'post': 'move'}),
         name='list-move'),
    path('tasks/<int:pk>/move/',
         TaskViewSet.as_view({'post': 'move'}),
         name='task-move'),
]

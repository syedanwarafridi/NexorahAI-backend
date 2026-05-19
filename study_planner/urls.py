from django.urls import path
from . import views

urlpatterns = [
    path('plan/', views.study_plan, name='study-plan'),
    path('sessions/', views.study_sessions, name='study-sessions'),
    path('stats/', views.planner_stats, name='planner-stats'),
    path('calendar/', views.calendar_events, name='calendar-events'),
    path('calendar/<int:event_id>/', views.calendar_event_detail, name='calendar-event-detail'),
]

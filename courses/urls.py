from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course-list'),
    path('my-courses/', views.my_courses, name='my-courses'),
    path('<slug:slug>/', views.course_detail, name='course-detail'),
    path('chapters/<int:chapter_id>/progress/', views.mark_chapter_progress, name='chapter-progress'),
    path('<int:course_id>/chat/', views.chat, name='course-chat'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course-list'),
    path('my-courses/', views.my_courses, name='my-courses'),
    path('weak-topics/', views.weak_topics, name='weak-topics'),
    path('chapters/<int:chapter_id>/progress/', views.mark_chapter_progress, name='chapter-progress'),
    path('chapters/<int:chapter_id>/quick-quiz/', views.chapter_quick_quiz, name='chapter-quick-quiz'),
    path('chapters/<int:chapter_id>/quick-quiz/submit/', views.submit_chapter_quiz, name='chapter-quick-quiz-submit'),
    path('domains/<int:domain_id>/assessment/', views.module_assessment, name='module-assessment'),
    path('domains/<int:domain_id>/assessment/submit/', views.submit_module_assessment, name='module-assessment-submit'),
    path('<int:course_id>/chat/', views.chat, name='course-chat'),
    path('<slug:slug>/', views.course_detail, name='course-detail'),
]

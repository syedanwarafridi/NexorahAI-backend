from django.urls import path
from . import views

urlpatterns = [
    path('topics/', views.topic_list, name='quiz-topics'),
    path('start/', views.start_session, name='quiz-start'),
    path('history/', views.session_history, name='quiz-history'),
    path('<int:session_id>/result/', views.session_result, name='quiz-result'),
    path('<int:session_id>/question/<int:question_number>/', views.get_question, name='quiz-question'),
    path('<int:session_id>/question/<int:question_number>/answer/', views.submit_answer, name='quiz-answer'),
]

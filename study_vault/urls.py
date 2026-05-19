from django.urls import path
from . import views

urlpatterns = [
    path('flashcards/', views.flashcard_list, name='flashcard-list'),
    path('keywords/', views.keyword_list, name='keyword-list'),
    path('case-studies/', views.case_study_list, name='case-study-list'),
    path('case-studies/<int:pk>/', views.case_study_detail, name='case-study-detail'),
    path('articles/', views.knowledge_article_list, name='article-list'),
    path('articles/<int:pk>/', views.knowledge_article_detail, name='article-detail'),
]

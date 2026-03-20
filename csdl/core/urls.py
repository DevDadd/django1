from django.urls import path
from . import views

urlpatterns = [
    path('questions/',    views.get_questions,      name='question-list'),
    path('signup/',       views.signup,             name='signup'),
    path('login/',        views.login,              name='login'),
    path('users/',        views.get_all_users,      name='get_all_users'),
    path('getuserdetail/', views.get_user_by_username, name='get_user_by_username'),
    path('updateuser/',   views.update_user,        name='update_user'),
    path('deleteuser/',   views.delete_user,        name='delete_user'),
    path('examdetail',    views.get_exam_detail,    name='get_exam_detail'),
    path('exams/',        views.get_all_exams,      name='get_all_exams'),
    path('createexam/',   views.create_exam,        name='create_exam'),
    path('updateexam/',   views.update_exam,        name='update_exam'),
    path('deleteexam/',   views.delete_exam,        name='delete_exam'),
    path('submitexam/<int:id>/', views.submit_exam, name='submit_exam'),
    # Mới thêm
    path('attempts/',     views.get_all_attempts,   name='get_all_attempts'),
    path('search/',       views.search_by_msv,      name='search_by_msv'),
]
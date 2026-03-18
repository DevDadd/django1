from django.db import connection
from .serializer import QuestionSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(['GET'])
def get_questions(request):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, content
            FROM questions
            """,
        )
        rows = cursor.fetchall()

    questions = [{"id": row[0], "content": row[1]} for row in rows]
    serializer = QuestionSerializer(questions, many=True)
    return Response(serializer.data)
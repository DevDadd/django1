from django.db import connection, transaction
from .serializer import QuestionSerializer, UserSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.auth.hashers import make_password

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

@api_view(['POST'])
def signup(request):
    id = request.GET.get('id')
    name = request.GET.get('name')
    username = request.GET.get('username')
    pwd = request.GET.get('pwd')

    if not all([name, username, pwd]):
        return Response({"error": "Missing fields"}, status=400)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (id, name, username, pwd)
            VALUES (%s, %s, %s, %s)
            """,
            [id, name, username, pwd]
        )

    return Response({"message": "User created successfully"}, status=201)

@api_view(['GET'])
def login(request):
    username = request.GET.get('username')
    pwd = request.GET.get('pwd')

    if not all([username, pwd]):
        return Response({"error": "Missing fields"}, status=400)
    
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, username, pwd
            FROM users
            WHERE username = %s AND pwd = %s
            """,
            [username, pwd]
        )
        row = cursor.fetchone()
        if row:
            return Response({"message": "Login successful"}, status=200)
        else:
            return Response({"error": "Invalid username or password"}, status=401)

@api_view(['GET'])
def get_all_users(request):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, username, pwd
            FROM users
            """
        )
        rows = cursor.fetchall()
        users = [{"id": row[0], "name": row[1], "username": row[2], "pwd": row[3]} for row in rows]
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

@api_view(['GET'])
def get_user_by_username(request):
    username = request.GET.get('username')
    if not username:
        return Response({"error": "Missing fields"}, status=400)
    
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, username, pwd
            FROM users
            WHERE username = %s
            """,
            [username]
        )
        row = cursor.fetchone()
        if row:
            users = {"id": row[0], "name": row[1], "username": row[2], "pwd": row[3]}
            serializer = UserSerializer(users, many=False)
            return Response(serializer.data, status=200)
        else:
            return Response({"error": "User not found"}, status=404)

@api_view(['PUT'])
def update_user(request):
    id = request.GET.get('id')
    name = request.GET.get('name')
    username = request.GET.get('username')
    pwd = request.GET.get('pwd')

    if not all([username]):
        return Response({"error": "Missing fields"}, status=400)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET name = %s, username = %s, pwd = %s
            WHERE id = %s
            """,
            [name, username, make_password(pwd), id]
        )

    return Response({"message": "User updated successfully"}, status=200)

@api_view(['DELETE'])
def delete_user(request):
    username = request.GET.get('username')
    if not username:
        return Response({"error": "Missing fields"}, status=400)
    
    with connection.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM users
            WHERE username = %s
            """,
            [username]
        )
    return Response({"message": "User deleted successfully"}, status=200)

@api_view(['GET'])
def get_exam_detail(request):
    id = request.GET.get('id')
    if not id:
        return Response({"error": "Missing fields"}, status=400)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, title, created_at, type
            FROM quizzes
            WHERE id = %s
            """,
            [id]
        )
        quiz = cursor.fetchone()

        if not quiz:
            return Response({"error": "Quiz not found"}, status=404)

        quiz_data = {
            "id": quiz[0],
            "title": quiz[1],
            "created_at": quiz[2],
            "type": quiz[3],
            "questions": []
        }

        cursor.execute(
            """
            SELECT 
                q.id as question_id,
                q.content as question_content,
                c.id as choice_id,
                c.content as choice_content,
                c.is_correct
            FROM quiz_questions qq
            JOIN questions q ON qq.question_id = q.id
            JOIN choices c ON c.question_id = q.id
            WHERE qq.quiz_id = %s
            ORDER BY q.id
            """,
            [id]
        )

        rows = cursor.fetchall()

    question_map = {}

    for row in rows:
        q_id = row[0]

        if q_id not in question_map:
            question_map[q_id] = {
                "id": q_id,
                "content": row[1],
                "choices": []
            }

        question_map[q_id]["choices"].append({
            "id": row[2],
            "content": row[3],
            # "is_correct": row[4] 
        })

    quiz_data["questions"] = list(question_map.values())

    return Response(quiz_data, status=200)

@api_view(['POST'])
def create_exam(request):
    title = request.data.get('title')
    quiz_type = request.data.get('type')
    questions = request.data.get('questions')

    if not title or quiz_type in (None, '') or not questions:
        return Response({"error": "Missing fields"}, status=400)

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO quizzes (title, created_at, type)
                    VALUES (%s, NOW(), %s)
                    RETURNING id
                    """,
                    [title, quiz_type]
                )
                quiz_id = cursor.fetchone()[0]

                for q in questions:
                    content = q.get('content')
                    choices = q.get('choices')

                    if not content or not choices:
                        raise Exception("Invalid question data")

                    cursor.execute(
                        """
                        INSERT INTO questions (content)
                        VALUES (%s)
                        RETURNING id
                        """,
                        [content]
                    )
                    question_id = cursor.fetchone()[0]

                    cursor.execute(
                        """
                        INSERT INTO quiz_questions (quiz_id, question_id)
                        VALUES (%s, %s)
                        """,
                        [quiz_id, question_id]
                    )

                    for c in choices:
                        c_content = c.get('content')
                        is_correct = c.get('is_correct', False)

                        cursor.execute(
                            """
                            INSERT INTO choices (question_id, content, is_correct)
                            VALUES (%s, %s, %s)
                            """,
                            [question_id, c_content, is_correct]
                        )

        return Response({
            "message": "Quiz created successfully",
            "quiz_id": quiz_id
        }, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['PUT'])
def update_exam(request):
    id = request.GET.get('id')
    if not id:
        return Response({"error": "Missing fields"}, status=400)
    title = request.data.get('title')
    quiz_type = request.data.get('type')
    questions = request.data.get('questions')

    if not title or not questions:
        return Response({"error": "Missing fields"}, status=400)

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:

                cursor.execute(
                    "SELECT id FROM quizzes WHERE id = %s",
                    [id]
                )
                if not cursor.fetchone():
                    return Response({"error": "Quiz not found"}, status=404)

                # Update title always; update `type` only when client provides it.
                if quiz_type in (None, ''):
                    cursor.execute(
                        """
                        UPDATE quizzes
                        SET title = %s
                        WHERE id = %s
                        """,
                        [title, id],
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE quizzes
                        SET title = %s, type = %s
                        WHERE id = %s
                        """,
                        [title, quiz_type, id],
                    )

                cursor.execute(
                    """
                    SELECT question_id FROM quiz_questions
                    WHERE quiz_id = %s
                    """,
                    [id]
                )
                old_question_ids = [row[0] for row in cursor.fetchall()]

                if old_question_ids:
                    cursor.execute(
                        """
                        DELETE FROM choices
                        WHERE question_id = ANY(%s)
                        """,
                        [old_question_ids]
                    )

                if old_question_ids:
                    cursor.execute(
                        """
                        DELETE FROM questions
                        WHERE id = ANY(%s)
                        """,
                        [old_question_ids]
                    )

                cursor.execute(
                    """
                    DELETE FROM quiz_questions
                    WHERE quiz_id = %s
                    """,
                    [id]
                )

                for q in questions:
                    content = q.get('content')
                    choices = q.get('choices')

                    if not content or not choices:
                        raise Exception("Invalid question")

                    cursor.execute(
                        """
                        INSERT INTO questions (content)
                        VALUES (%s)
                        RETURNING id
                        """,
                        [content]
                    )
                    question_id = cursor.fetchone()[0]

                    cursor.execute(
                        """
                        INSERT INTO quiz_questions (quiz_id, question_id)
                        VALUES (%s, %s)
                        """,
                        [id, question_id]
                    )

                    for c in choices:
                        cursor.execute(
                            """
                            INSERT INTO choices (question_id, content, is_correct)
                            VALUES (%s, %s, %s)
                            """,
                            [
                                question_id,
                                c.get('content'),
                                c.get('is_correct', False)
                            ]
                        )

        return Response({"message": "Quiz updated successfully"}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
@api_view(['DELETE'])
def delete_exam(request):
    id = request.GET.get('id')
    if not id:
        return Response({"error": "Missing fields"}, status=400)
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT question_id FROM quiz_questions
                    WHERE quiz_id = %s
                    """,
                    [id]
                )
                question_ids = [row[0] for row in cursor.fetchall()]

                if question_ids:
                    cursor.execute(
                        "DELETE FROM choices WHERE question_id = ANY(%s)",
                        [question_ids]
                    )
                    cursor.execute(
                        "DELETE FROM questions WHERE id = ANY(%s)",
                        [question_ids]
                    )

                cursor.execute(
                    "DELETE FROM quiz_questions WHERE quiz_id = %s",
                    [id]
                )

                cursor.execute(
                    "DELETE FROM quizzes WHERE id = %s",
                    [id]
                )

        return Response({"message": "Deleted successfully"})

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
def submit_exam(request, id):
    user_id = request.data.get('user_id')
    answers = request.data.get('answers')

    if not user_id or not answers:
        return Response({"error": "Missing fields"}, status=400)

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:

                cursor.execute(
                    "SELECT id FROM quizzes WHERE id = %s",
                    [id]
                )
                if not cursor.fetchone():
                    return Response({"error": "Quiz not found"}, status=404)

                cursor.execute(
                    """
                    SELECT q.id, c.id
                    FROM quiz_questions qq
                    JOIN questions q ON qq.question_id = q.id
                    JOIN choices c ON c.question_id = q.id
                    WHERE qq.quiz_id = %s AND c.is_correct = TRUE
                    """,
                    [id]
                )

                correct_map = {
                    row[0]: row[1]
                    for row in cursor.fetchall()
                }

                score = 0
                total = len(correct_map)

                for ans in answers:
                    if correct_map.get(ans.get('question_id')) == ans.get('choice_id'):
                        score += 1

                cursor.execute(
                    """
                    INSERT INTO attempts (user_id, quiz_id, score, created_at)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id
                    """,
                    [user_id, id, score]
                )
                attempt_id = cursor.fetchone()[0]

                for ans in answers:
                    cursor.execute(
                        """
                        INSERT INTO answers (attempt_id, question_id, choice_id)
                        VALUES (%s, %s, %s)
                        """,
                        [
                            attempt_id,
                            ans.get('question_id'),
                            ans.get('choice_id')
                        ]
                    )

        return Response({
            "message": "Submit success",
            "score": score,
            "total": total
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)
from django.db import connection, transaction
from .serializer import QuestionSerializer, UserSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.auth.hashers import make_password

@api_view(['GET'])
def get_questions(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, content FROM questions")
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
            "INSERT INTO users (id, name, username, pwd) VALUES (%s, %s, %s, %s)",
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
            "SELECT id, name, username, pwd FROM users WHERE username = %s AND pwd = %s",
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
        cursor.execute("SELECT id, name, username, pwd FROM users")
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
            "SELECT id, name, username, pwd FROM users WHERE username = %s", [username]
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
            "UPDATE users SET name = %s, username = %s, pwd = %s WHERE id = %s",
            [name, username, make_password(pwd), id]
        )
    return Response({"message": "User updated successfully"}, status=200)

@api_view(['DELETE'])
def delete_user(request):
    username = request.GET.get('username')
    if not username:
        return Response({"error": "Missing fields"}, status=400)
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE username = %s", [username])
    return Response({"message": "User deleted successfully"}, status=200)

@api_view(['GET'])
def get_exam_detail(request):
    id = request.GET.get('id')
    if not id:
        return Response({"error": "Missing fields"}, status=400)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, title, created_at, type FROM quizzes WHERE id = %s", [id]
        )
        quiz = cursor.fetchone()
        if not quiz:
            return Response({"error": "Quiz not found"}, status=404)

        quiz_data = {
            "id": quiz[0], "title": quiz[1],
            "created_at": quiz[2], "type": quiz[3], "questions": []
        }

        cursor.execute(
            """
            SELECT q.id, q.content, c.id, c.content, c.is_correct
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
            question_map[q_id] = {"id": q_id, "content": row[1], "choices": []}
        question_map[q_id]["choices"].append({"id": row[2], "content": row[3]})

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
                    "INSERT INTO quizzes (title, created_at, type) VALUES (%s, NOW(), %s) RETURNING id",
                    [title, quiz_type]
                )
                quiz_id = cursor.fetchone()[0]
                for q in questions:
                    content = q.get('content')
                    choices = q.get('choices')
                    if not content or not choices:
                        raise Exception("Invalid question data")
                    cursor.execute(
                        "INSERT INTO questions (content) VALUES (%s) RETURNING id", [content]
                    )
                    question_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO quiz_questions (quiz_id, question_id) VALUES (%s, %s)",
                        [quiz_id, question_id]
                    )
                    for c in choices:
                        cursor.execute(
                            "INSERT INTO choices (question_id, content, is_correct) VALUES (%s, %s, %s)",
                            [question_id, c.get('content'), c.get('is_correct', False)]
                        )
        return Response({"message": "Quiz created successfully", "quiz_id": quiz_id}, status=201)
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
                cursor.execute("SELECT id FROM quizzes WHERE id = %s", [id])
                if not cursor.fetchone():
                    return Response({"error": "Quiz not found"}, status=404)
                if quiz_type in (None, ''):
                    cursor.execute("UPDATE quizzes SET title = %s WHERE id = %s", [title, id])
                else:
                    cursor.execute(
                        "UPDATE quizzes SET title = %s, type = %s WHERE id = %s",
                        [title, quiz_type, id]
                    )
                cursor.execute(
                    "SELECT question_id FROM quiz_questions WHERE quiz_id = %s", [id]
                )
                old_question_ids = [row[0] for row in cursor.fetchall()]
                if old_question_ids:
                    cursor.execute("DELETE FROM choices WHERE question_id = ANY(%s)", [old_question_ids])
                    cursor.execute("DELETE FROM questions WHERE id = ANY(%s)", [old_question_ids])
                cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", [id])
                for q in questions:
                    content = q.get('content')
                    choices = q.get('choices')
                    if not content or not choices:
                        raise Exception("Invalid question")
                    cursor.execute(
                        "INSERT INTO questions (content) VALUES (%s) RETURNING id", [content]
                    )
                    question_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO quiz_questions (quiz_id, question_id) VALUES (%s, %s)",
                        [id, question_id]
                    )
                    for c in choices:
                        cursor.execute(
                            "INSERT INTO choices (question_id, content, is_correct) VALUES (%s, %s, %s)",
                            [question_id, c.get('content'), c.get('is_correct', False)]
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
                cursor.execute("SELECT question_id FROM quiz_questions WHERE quiz_id = %s", [id])
                question_ids = [row[0] for row in cursor.fetchall()]
                if question_ids:
                    cursor.execute("DELETE FROM choices WHERE question_id = ANY(%s)", [question_ids])
                    cursor.execute("DELETE FROM questions WHERE id = ANY(%s)", [question_ids])
                cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", [id])
                cursor.execute("DELETE FROM quizzes WHERE id = %s", [id])
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
                cursor.execute("SELECT id FROM quizzes WHERE id = %s", [id])
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
                correct_map = {row[0]: row[1] for row in cursor.fetchall()}

                score = 0
                total = len(correct_map)
                for ans in answers:
                    if correct_map.get(ans.get('question_id')) == ans.get('choice_id'):
                        score += 1

                cursor.execute(
                    "INSERT INTO attempts (user_id, quiz_id, score, created_at) VALUES (%s, %s, %s, NOW()) RETURNING id",
                    [user_id, id, score]
                )
                attempt_id = cursor.fetchone()[0]

                for ans in answers:
                    cursor.execute(
                        "INSERT INTO answers (attempt_id, question_id, choice_id) VALUES (%s, %s, %s)",
                        [attempt_id, ans.get('question_id'), ans.get('choice_id')]
                    )

        return Response({
            "message": "Submit success",
            "score": score,
            "total": total,
            "correct_answers": correct_map
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def get_all_exams(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT q.id, q.title, q.type, COUNT(qq.question_id) as q_count
                FROM quizzes q
                LEFT JOIN quiz_questions qq ON q.id = qq.quiz_id
                GROUP BY q.id, q.title, q.type
                ORDER BY q.created_at DESC
            """)
            rows = cursor.fetchall()
        exams = [{"id": r[0], "title": r[1], "type": r[2], "question_count": r[3]} for r in rows]
        return Response(exams, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def get_all_attempts(request):
    """
    Thống kê tất cả lượt làm bài.
    total = số câu hỏi của đề thi đó (đếm từ quiz_questions)
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    u.id                        AS msv,
                    u.name                      AS ho_ten,
                    qz.title                    AS ten_de,
                    a.score,
                    COUNT(qq.question_id)       AS total,
                    a.created_at
                FROM attempts a
                JOIN users         u  ON a.user_id  = u.id
                JOIN quizzes       qz ON a.quiz_id  = qz.id
                LEFT JOIN quiz_questions qq ON qq.quiz_id = qz.id
                GROUP BY u.id, u.name, qz.title, a.score, a.created_at
                ORDER BY a.created_at DESC
            """)
            rows = cursor.fetchall()

        data = [
            {
                "msv":        row[0],
                "ho_ten":     row[1],
                "ten_de":     row[2],
                "score":      row[3],
                "total":      row[4],
                "created_at": str(row[5])
            }
            for row in rows
        ]
        return Response(data, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def search_by_msv(request):
    """
    Tra cứu sinh viên theo MSV, trả về thông tin + lịch sử làm bài.
    """
    msv = request.GET.get('msv', '').strip()
    if not msv:
        return Response({"error": "Missing msv"}, status=400)
    try:
        with connection.cursor() as cursor:
            # Thông tin sinh viên
            cursor.execute(
                "SELECT id, name, username FROM users WHERE id = %s", [msv]
            )
            user_row = cursor.fetchone()
            if not user_row:
                return Response({"error": "Không tìm thấy sinh viên với MSV này"}, status=404)

            # Lịch sử làm bài + tính total từ quiz_questions
            cursor.execute("""
                SELECT
                    qz.title,
                    a.score,
                    COUNT(qq.question_id) AS total,
                    a.created_at
                FROM attempts a
                JOIN quizzes qz ON a.quiz_id = qz.id
                LEFT JOIN quiz_questions qq ON qq.quiz_id = qz.id
                WHERE a.user_id = %s
                GROUP BY qz.title, a.score, a.created_at
                ORDER BY a.created_at DESC
            """, [msv])
            attempt_rows = cursor.fetchall()

        attempts = [
            {
                "ten_de":     row[0],
                "score":      row[1],
                "total":      row[2],
                "created_at": str(row[3])
            }
            for row in attempt_rows
        ]

        return Response({
            "msv":      user_row[0],
            "ho_ten":   user_row[1],
            "username": user_row[2],
            "attempts": attempts
        }, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def add_user(request):
    id = request.GET.get('id')
    name = request.GET.get('name')
    username = request.GET.get('username')
    pwd = request.GET.get('pwd')
    if not all([id, name, username, pwd]):
        return Response({"error": "Missing fields"}, status=400)
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO users (id, name, username, pwd) VALUES (%s, %s, %s, %s)", [id, name, username, pwd])
    return Response({"message": "User added successfully"}, status=201)
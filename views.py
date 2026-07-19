from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
import pymysql


def get_db_connection():
    return pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="root",
        database="webdb14",
        cursorclass=pymysql.cursors.DictCursor
    )


def ensure_single_admin():
    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("SELECT id FROM users1 WHERE role='admin'")
        admin = cur.fetchone()

        if not admin:
            cur.execute("""
                INSERT INTO users1
                (username,email,password,mobile,address,role,approved)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                "admin",
                "admin@gmail.com",
                "admin",
                "1234567890",
                "Hyderabad",
                "admin",
                1
            ))
            con.commit()


@api_view(["POST"])
def register_api(request):
    username = request.data.get("username")
    email = request.data.get("email")
    password = request.data.get("password")
    confirm = request.data.get("confirm_password")
    mobile = request.data.get("mobile")
    address = request.data.get("address")

    if password != confirm:
        return Response({"error": "Passwords do not match"})

    if not all([username, email, password, mobile, address]):
        return Response({"error": "All fields are required"})
    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("SELECT id FROM users1 WHERE username=%s", (username,))
        if cur.fetchone():
            return Response({"error": "Username already exists"})

        cur.execute("SELECT id FROM users1 WHERE email=%s", (email,))
        if cur.fetchone():
            return Response({"error": "Email already exists"})

        cur.execute("SELECT id FROM users1 WHERE mobile=%s", (mobile,))
        if cur.fetchone():
            return Response({"error": "Mobile already exists"})

        cur.execute("""
            INSERT INTO users1
            (username,email,password,mobile,address,role,approved)
            VALUES (%s,%s,%s,%s,%s,'user',0)
        """, (username, email, password, mobile, address))
        con.commit()

    return Response({"success": "Account created. Awaiting Admin approval"})


@api_view(["POST"])
def login_api(request):
    ensure_single_admin()

    username = request.data.get("username")
    password = request.data.get("password")

    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("""
            SELECT * FROM users1
            WHERE username=%s AND password=%s
        """, (username, password))
        user = cur.fetchone()

    if not user:
        return Response({"error": "Invalid username or password"})

    if user["approved"] == 0:
        return Response({"error": "Account not approved by admin"})

    return Response({
        "success": "Login successful",
        "username": user["username"],
        "role": user["role"]
    })


@api_view(["GET"])
def user_details_api(request):
    username = request.GET.get("username")

    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users1 WHERE username=%s", (username,))
        user = cur.fetchone()
    if not user:
        return Response({"error": "User not found"})
    return Response({"user": user})


@api_view(["GET"])
def admin_users_api(request):
    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users1 WHERE role='user'")
        users = cur.fetchall()

    return Response({"users": users})


@api_view(["POST"])
def approve_user_api(request):
    username = request.data.get("username")

    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users1 SET approved=1 WHERE username=%s",
            (username,)
        )
        con.commit()

    return Response({"success": "User approved successfully"})


@api_view(["POST"])
def submit_crop_request_api(request):
    username = request.data.get("username")
    crop_name = request.data.get("crop_name")
    land_area = request.data.get("land_area")
    soil_type = request.data.get("soil_type")

    if not all([username, crop_name, land_area, soil_type]):
        return Response({"error": "All fields required"})

    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO crop_requests (username, crop_name, land_area, soil_type)
            VALUES (%s,%s,%s,%s)
        """, (username, crop_name, land_area, soil_type))
        con.commit()

    return Response({"success": "Crop request submitted successfully"})

@api_view(["GET"])
def admin_crop_requests_api(request):
    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("""
            SELECT * FROM crop_requests
            ORDER BY id DESC
        """)
        data = cur.fetchall()

    return Response({"requests": data})

@api_view(["POST"])
def send_crop_response_api(request):
    request_id = request.data.get("request_id")
    seed_quantity = request.data.get("seed_quantity")
    fertilizer = request.data.get("fertilizer")
    pesticide = request.data.get("pesticide")
    irrigation = request.data.get("irrigation")
    remarks = request.data.get("remarks")

    if not all([request_id, seed_quantity, fertilizer, pesticide, irrigation]):
        return Response({"error": "All fields required"})

    con = get_db_connection()
    with con:
        cur = con.cursor()

        cur.execute("""
            INSERT INTO crop_responses
            (request_id, seed_quantity, fertilizer, pesticide, irrigation, remarks)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            request_id, seed_quantity, fertilizer,
            pesticide, irrigation, remarks
        ))

        cur.execute("""
            UPDATE crop_requests
            SET status='Responded'
            WHERE id=%s
        """, (request_id,))

        con.commit()

    return Response({"success": "Crop advisory sent to farmer"})

@api_view(["GET"])
def view_crop_response_api(request):
    username = request.GET.get("username")

    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("""
            SELECT
                cr.crop_name,
                resp.seed_quantity,
                resp.fertilizer,
                resp.pesticide,
                resp.irrigation,
                resp.remarks
            FROM crop_requests cr
            JOIN crop_responses resp
            ON cr.id = resp.request_id
            WHERE cr.username=%s
            ORDER BY resp.id DESC
        """, (username,))
        data = cur.fetchall()

    return Response({"responses": data})

@api_view(["GET"])
def admin_pending_crop_requests_api(request):
    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("""
            SELECT * FROM crop_requests
            WHERE status='Pending'
            ORDER BY id DESC
        """)
        data = cur.fetchall()

    return Response({"requests": data})

@api_view(["POST"])
def delete_crop_request_api(request):
    request_id = request.data.get("id")

    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("DELETE FROM crop_requests WHERE id=%s", (request_id,))
        con.commit()

    return Response({"success": "Crop request deleted"})

@api_view(["GET"])
def user_crop_requests_api(request):
    username = request.GET.get("username")

    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("""
            SELECT crop_name, land_area, soil_type, status
            FROM crop_requests
            WHERE username=%s
            ORDER BY id DESC
        """, (username,))
        data = cur.fetchall()

    return Response({"requests": data})

@api_view(["POST"])
def mark_response_read_api(request):
    request_id = request.data.get("request_id")

    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("""
            UPDATE crop_requests
            SET status='Completed'
            WHERE id=%s
        """, (request_id,))
        con.commit()

    return Response({"success": "Response marked as read"})

@api_view(["GET"])
def admin_response_history_api(request):
    con = get_db_connection()
    with con:
        cur = con.cursor()
        cur.execute("""
            SELECT
                cr.username,
                cr.crop_name,
                cr.land_area,
                cr.soil_type,
                resp.seed_quantity,
                resp.fertilizer,
                resp.pesticide,
                resp.irrigation,
                resp.remarks
            FROM crop_requests cr
            JOIN crop_responses resp
            ON cr.id = resp.request_id
            ORDER BY resp.id DESC
        """)
        data = cur.fetchall()

    return Response({"responses": data})

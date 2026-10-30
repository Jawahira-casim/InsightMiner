from db import get_connection

def log_activity(username, activity):

    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    INSERT INTO activity_logs (username, activity)
    VALUES (%s, %s)
    """

    cursor.execute(sql, (username, activity))

    conn.commit()
    cursor.close()
    conn.close()
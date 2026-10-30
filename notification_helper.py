from db import get_connection

def add_notification(username, message):

    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    INSERT INTO notifications (username, message)
    VALUES (%s, %s)
    """

    cursor.execute(sql, (username, message))

    conn.commit()
    cursor.close()
    conn.close()
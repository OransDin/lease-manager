from lease_manager.db import get_conn

def add_note(unit_id, note, author):
    with get_conn() as con, con.cursor() as cur:
        cur.execute(
            "INSERT INTO unit_notes(unit_id, note_text, author) VALUES (%s,%s,%s)",
            (unit_id, note, author),
        )
        con.commit()

def get_notes(unit_id):
    with get_conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT id, note_text, COALESCE(author,'' ) AS author, created_at
            FROM unit_notes
            WHERE unit_id=%s
            ORDER BY created_at DESC
        """, (unit_id,))
        return cur.fetchall()

def delete_note(note_id: int) -> bool:
    with get_conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM unit_notes WHERE id=%s RETURNING id", (note_id,))
        deleted = cur.fetchone()
        con.commit()
        return bool(deleted)

def update_note(note_id: int, new_text: str) -> bool:
    with get_conn() as con, con.cursor() as cur:
        cur.execute(
            "UPDATE unit_notes SET note_text=%s, created_at=now() WHERE id=%s RETURNING id",
            (new_text, note_id),
        )
        updated = cur.fetchone()
        con.commit()
        return bool(updated)

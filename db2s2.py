def conexion(sql):
    import os
    import sys
    from pathlib import Path

    from dotenv import load_dotenv

    # Esto localiza la carpeta donde está el .exe o el script actual:
    if getattr(sys, "frozen", False):
        # Si está corriendo compilado como ejecutable (.exe)
        base_dir = Path(sys.executable).parent
    else:
        # Si está corriendo directamente como script de Python
        base_dir = Path(__file__).parent

    # Carga explícitamente el archivo .env ubicado en esa misma carpeta
    load_dotenv(base_dir / ".env")

    import ibm_db

    conn_str = (
        "DATABASE=DALLASD;"
        "HOSTNAME=10.1.14.102;"
        "PORT=5045;"
        "PROTOCOL=TCPIP;"
        "UID=TSOPSSB;"
        f"PWD={os.getenv('ZOSMF_PASS', '')};"
    )
    conn = None
    resultado = None
    try:
        conn = ibm_db.connect(conn_str, "", "")
        stmt = ibm_db.exec_immediate(conn, sql)

        if stmt is False:
            print("ERROR ejecutando SQL:")
            print(ibm_db.stmt_errormsg())
        else:
            filas = 0
            while True:
                if ibm_db.num_fields(stmt) > 0:  # es un SELECT
                    row = ibm_db.fetch_assoc(stmt)
                else:
                    row = None

                if not row:
                    break

                if resultado is None:  # guarda la primera fila
                    resultado = row
                filas += 1

    except Exception as e:
        print("ERROR DE CONEXIÓN:")
        print(e)
    finally:
        if conn:
            ibm_db.close(conn)

    return resultado

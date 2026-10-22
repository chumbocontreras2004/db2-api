def conexion(sql):
    import ibm_db

    conn_str = (
        "DATABASE=DALLASD;"
        "HOSTNAME=10.1.14.102;"
        "PORT=5045;"
        "PROTOCOL=TCPIP;"
        "UID=TSOPSSB;"
        "PWD=Adrian17;"
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

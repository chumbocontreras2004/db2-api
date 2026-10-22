def juego_ppt(eleccion):
    from random import random

    from db2s2 import conexion

    V_RANDOM = random()

    fila = conexion(f"""SELECT 
                                CASE 
                                    WHEN {V_RANDOM} < PROB_PIEDRA THEN 'PIEDRA'
                                    WHEN {V_RANDOM} < (PROB_PIEDRA + PROB_PAPEL) THEN 'PAPEL'
                                    ELSE 'TIJERA'
                                END AS ELECCION_BOT
                            FROM TSOPSSB.PPT""")
    rival = fila["ELECCION_BOT"].lower()
    gana_a = {"piedra": "tijera", "papel": "piedra", "tijera": "papel"}
    if eleccion == rival:
        resultado = "empate"
    elif gana_a[eleccion] == rival:
        resultado = "gana"
    else:
        resultado = "pierde"
    return rival, resultado

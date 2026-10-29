from db2s2 import conexion
from juego import juego_ppt

EMOJI = {"piedra": "✊", "papel": "✋", "tijera": "✌️"}


def crear_juego(ganancia, perdida, preciobs, bsprob, precioq, aumentomult, basepot):
    class Juego:
        def __init__(self):
            self.eliminar()
            self.crear()

        # ---------------- CREADOR (INTACTO) -----------------
        def crear(self):
            conexion(
                """CREATE TABLESPACE SPACEPPT
                    IN PSSDB0B
                    USING STOGROUP SYSDEFLT
                    PRIQTY 720
                    SECQTY 720
                    LOCKSIZE ROW"""
            )
            conexion(
                """CREATE TABLE TSOPSSB.PPT (
                    PROB_PIEDRA DECIMAL(5, 4),
                    PROB_PAPEL DECIMAL(5, 4),
                    PROB_TIJERA DECIMAL(5, 4),
                    DINERO INT,
                    RACHA INT,
                    MULTIPLICADOR DECIMAL(5, 2))
                    IN PSSDB0B.SPACEPPT"""
            )
            conexion(
                """INSERT INTO TSOPSSB.PPT (PROB_PIEDRA, PROB_PAPEL, PROB_TIJERA, DINERO, RACHA, MULTIPLICADOR) 
                VALUES (0.3333, 0.3333, 0.3333, 0, 0, 1)"""
            )
            self.select()

        # ----------------- ELIMINADOR (INTACTO) -----------------
        def eliminar(self):
            conexion("DROP TABLE TSOPSSB.PPT")

        # ---------------- SELECCIONADOR (INTACTO) -----------------
        def select(self):
            self.datos = conexion("SELECT * FROM TSOPSSB.PPT")
            self.monedas = self.datos["DINERO"]
            self.racha = self.datos["RACHA"]
            self.prob = {
                "piedra": float(self.datos["PROB_PIEDRA"].replace(",", ".")),
                "papel": float(self.datos["PROB_PAPEL"].replace(",", ".")),
                "tijera": float(self.datos["PROB_TIJERA"].replace(",", ".")),
            }
            self.multiplicador = float(self.datos["MULTIPLICADOR"].replace(",", "."))

        # ---------------- ACTUALIZADOR (INTACTO) -----------------
        def updatear(self):
            conexion(
                f"""UPDATE TSOPSSB.PPT 
                SET PROB_PIEDRA = {self.prob["piedra"]}, 
                PROB_PAPEL = {self.prob["papel"]}, 
                PROB_TIJERA = {self.prob["tijera"]},
                DINERO = {self.monedas},
                RACHA = {self.racha},
                MULTIPLICADOR = {self.multiplicador}
                """
            )

        def obtener_estado(self):
            self.select()
            return {
                "monedas": self.monedas,
                "racha": self.racha,
                "multiplicador": self.multiplicador,
                "prob": self.prob,
                "preciobs": preciobs,
                "precioq": precioq,
            }

        def reiniciar(self):
            self.eliminar()
            self.crear()
            return self.obtener_estado()

        # ---------------- TU LÓGICA AQUÍ (100% INTACTA) ----------------
        def jugar(self, eleccion):
            rival, resultado = juego_ppt(eleccion)
            if isinstance(rival, str):
                rival = rival.lower()
            self.select()

            if resultado == "pierde":
                self.monedas = max(self.monedas - perdida, 0)
                self.racha = 0
                self.multiplicador = 1
                mensaje = "😢 Pierdes"
            elif resultado == "gana":
                self.monedas = int(
                    round(self.monedas + ganancia * self.multiplicador, 0)
                )
                self.racha += 1
                if basepot == 0:
                    self.multiplicador = 1 + self.racha * aumentomult
                else:
                    self.multiplicador = basepot ** (self.racha * aumentomult)
                mensaje = "🎉 ¡Ganas!"
            else:
                self.racha = 0
                self.multiplicador = 1
                mensaje = "🤝 Empate"

            self.updatear()

            ganado = self.racha >= 10
            if ganado:
                mensaje = "🏆 ¡RACHA DE 10! ¡HAS GANADO! 🏆"

            return {
                "rival": rival,
                "resultado": resultado,
                "mensaje": mensaje,
                "monedas": self.monedas,
                "racha": self.racha,
                "multiplicador": self.multiplicador,
                "victoria_final": ganado,
            }

        def comprar(self, item):
            self.select()
            agotadas = [baza for baza, probab in self.prob.items() if probab == 0]
            if len(agotadas) == 2:
                return {
                    "mensaje": "No puedes comprar nada. Solo le queda una baza al rival.",
                    "estado": self.obtener_estado(),
                }

            if item == "mas_piedra":
                if self.monedas < preciobs:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["piedra"] == 1:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar piedra ya era 1.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "La probabilidad de que el rival saque piedra ha aumentado."
                self.monedas = self.monedas - preciobs
                if len(agotadas) == 1:
                    self.prob["piedra"] = min(1, self.prob["piedra"] + bsprob)
                    restante = next(
                        b for b in self.prob if b not in ("piedra", agotadas[0])
                    )
                    self.prob[restante] = max(0, self.prob[restante] - bsprob)
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                if self.prob["piedra"] > 1 - bsprob:
                    self.prob["papel"] = 0
                    self.prob["tijera"] = 0
                    self.prob["piedra"] = 1
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                self.prob["piedra"] = min(1, self.prob["piedra"] + bsprob)
                self.prob["papel"] = max(0, self.prob["papel"] - bsprob / 2)
                self.prob["tijera"] = max(0, self.prob["tijera"] - bsprob / 2)

            if item == "mas_papel":
                if self.monedas < preciobs:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["papel"] == 1:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar papel ya era 1.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "La probabilidad de que el rival saque papel ha aumentado."
                self.monedas = self.monedas - preciobs
                if len(agotadas) == 1:
                    self.prob["papel"] = min(1, self.prob["papel"] + bsprob)
                    restante = next(
                        b for b in self.prob if b not in ("papel", agotadas[0])
                    )
                    self.prob[restante] = max(0, self.prob[restante] - bsprob)
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                if self.prob["papel"] > 1 - bsprob:
                    self.prob["piedra"] = 0
                    self.prob["tijera"] = 0
                    self.prob["papel"] = 1
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                self.prob["papel"] = min(1, self.prob["papel"] + bsprob)
                self.prob["piedra"] = max(0, self.prob["piedra"] - bsprob / 2)
                self.prob["tijera"] = max(0, self.prob["tijera"] - bsprob / 2)

            if item == "mas_tijera":
                if self.monedas < preciobs:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["tijera"] == 1:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar tijera ya era 1.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "La probabilidad de que el rival saque tijera ha aumentado."
                self.monedas = self.monedas - preciobs
                if len(agotadas) == 1:
                    self.prob["tijera"] = min(1, self.prob["tijera"] + bsprob)
                    restante = next(
                        b for b in self.prob if b not in ("tijera", agotadas[0])
                    )
                    self.prob[restante] = max(0, self.prob[restante] - bsprob)
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                if self.prob["tijera"] > 1 - bsprob:
                    self.prob["piedra"] = 0
                    self.prob["papel"] = 0
                    self.prob["tijera"] = 1
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                self.prob["tijera"] = min(1, self.prob["tijera"] + bsprob)
                self.prob["piedra"] = max(0, self.prob["piedra"] - bsprob / 2)
                self.prob["papel"] = max(0, self.prob["papel"] - bsprob / 2)

            if item == "menos_piedra":
                if self.monedas < preciobs:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["piedra"] == 0:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar piedra ya era cero.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "La probabilidad de que el rival saque piedra ha disminuido."
                self.monedas = self.monedas - preciobs
                if len(agotadas) == 1:
                    self.prob["piedra"] = max(0, self.prob["piedra"] - bsprob)
                    restante = next(
                        b for b in self.prob if b not in ("piedra", agotadas[0])
                    )
                    self.prob[restante] = min(1, self.prob[restante] + bsprob)
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                if self.prob["piedra"] < bsprob:
                    self.prob["papel"] = (
                        self.prob["papel"] + (self.prob["piedra"] / 2)
                    ) / 0.9999
                    self.prob["tijera"] = (
                        self.prob["tijera"] + (self.prob["piedra"] / 2)
                    ) / 0.9999
                    self.prob["piedra"] = 0
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                self.prob["piedra"] = max(0, self.prob["piedra"] - bsprob)
                self.prob["papel"] = min(1, self.prob["papel"] + bsprob / 2)
                self.prob["tijera"] = min(1, self.prob["tijera"] + bsprob / 2)

            if item == "menos_papel":
                if self.monedas < preciobs:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["papel"] == 0:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar papel ya era cero.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "La probabilidad de que el rival saque papel ha disminuido."
                self.monedas = self.monedas - preciobs
                if len(agotadas) == 1:
                    self.prob["papel"] = max(0, self.prob["papel"] - bsprob)
                    restante = next(
                        b for b in self.prob if b not in ("papel", agotadas[0])
                    )
                    self.prob[restante] = min(1, self.prob[restante] + bsprob)
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                if self.prob["papel"] < bsprob:
                    self.prob["piedra"] = (
                        self.prob["piedra"] + (self.prob["papel"] / 2)
                    ) / 0.9999
                    self.prob["tijera"] = (
                        self.prob["tijera"] + (self.prob["papel"] / 2)
                    ) / 0.9999
                    self.prob["papel"] = 0
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                self.prob["papel"] = max(0, self.prob["papel"] - bsprob)
                self.prob["piedra"] = min(1, self.prob["piedra"] + bsprob / 2)
                self.prob["tijera"] = min(1, self.prob["tijera"] + bsprob / 2)

            if item == "menos_tijera":
                if self.monedas < preciobs:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["tijera"] == 0:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar tijera ya era cero.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "La probabilidad de que el rival saque tijera ha disminuido."
                self.monedas = self.monedas - preciobs
                if len(agotadas) == 1:
                    self.prob["tijera"] = max(0, self.prob["tijera"] - bsprob)
                    restante = next(
                        b for b in self.prob if b not in ("tijera", agotadas[0])
                    )
                    self.prob[restante] = min(1, self.prob[restante] + bsprob)
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                if self.prob["tijera"] < bsprob:
                    self.prob["piedra"] = (
                        self.prob["piedra"] + (self.prob["tijera"] / 2)
                    ) / 0.9999
                    self.prob["papel"] = (
                        self.prob["papel"] + (self.prob["tijera"] / 2)
                    ) / 0.9999
                    self.prob["tijera"] = 0
                    self.updatear()
                    return {"mensaje": mensaje, "estado": self.obtener_estado()}
                self.prob["tijera"] = max(0, self.prob["tijera"] - bsprob)
                self.prob["piedra"] = min(1, self.prob["piedra"] + bsprob / 2)
                self.prob["papel"] = min(1, self.prob["papel"] + bsprob / 2)

            if item == "quitar_piedra":
                if self.monedas < precioq:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["piedra"] == 0:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar piedra ya era cero.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "El rival ya no puede sacar piedra."
                self.monedas = self.monedas - precioq
                p, t = self.prob["papel"], self.prob["tijera"]
                self.prob["piedra"] = 0
                self.prob["papel"] = p / (p + t)
                self.prob["tijera"] = t / (p + t)

            if item == "quitar_papel":
                if self.monedas < precioq:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["papel"] == 0:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar papel ya era cero.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "El rival ya no puede sacar papel."
                self.monedas = self.monedas - precioq
                p, t = self.prob["piedra"], self.prob["tijera"]
                self.prob["piedra"] = p / (p + t)
                self.prob["papel"] = 0
                self.prob["tijera"] = t / (p + t)

            if item == "quitar_tijera":
                if self.monedas < precioq:
                    return {
                        "mensaje": "No tienes suficientes monedas para comprar.",
                        "estado": self.obtener_estado(),
                    }
                if self.prob["tijera"] == 0:
                    return {
                        "mensaje": "No se han gastado monedas. La probabilidad de sacar tijera ya era cero.",
                        "estado": self.obtener_estado(),
                    }
                mensaje = "El rival ya no puede sacar tijera."
                self.monedas = self.monedas - precioq
                pi, pa = self.prob["piedra"], self.prob["papel"]
                self.prob["piedra"] = pi / (pi + pa)
                self.prob["papel"] = pa / (pi + pa)
                self.prob["tijera"] = 0

            self.updatear()
            return {"mensaje": mensaje, "estado": self.obtener_estado()}

    return Juego()

def ppt(ganancia, perdida, preciobs, precioq, aumentomult, basepot):
    import tkinter as tk

    from db2s2 import conexion
    from juego import juego_ppt

    EMOJI = {"piedra": "✊", "papel": "✋", "tijera": "✌️"}

    class Juego(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Piedra, Papel o Tijeras")
            self.configure(bg="#f4f1ea")
            self.resizable(False, False)
            self.eliminar()
            self.crear()
            self.botones_tienda = {}
            self._construir()
            self.update_idletasks()  # calcula el tamaño real del contenido
            ancho = self.winfo_reqwidth() + 30
            alto = self.winfo_reqheight() + 20
            self.geometry(f"{ancho}x{alto}")

        # ---------------- INTERFAZ ----------------
        def _construir(self):
            # Cabecera con contador de monedas
            cab = tk.Frame(self, bg="#f4f1ea")
            cab.pack(fill="x", padx=16, pady=12)
            tk.Label(
                cab,
                text="Piedra, Papel o Tijeras",
                font=("Arial", 16, "bold"),
                bg="#f4f1ea",
            ).pack(side="left")
            self.lbl_monedas = tk.Label(
                cab,
                text="🪙 0",
                font=("Arial", 15, "bold"),
                bg="white",
                fg="#222",
                padx=12,
                pady=4,
                highlightbackground="#f2b705",
                highlightthickness=2,
            )
            self.lbl_monedas.pack(side="right")
            self.set_monedas(self.monedas)
            # Arena
            arena = tk.Frame(
                self, bg="white", highlightbackground="#e2ddd0", highlightthickness=1
            )
            arena.pack(fill="x", padx=16, pady=8, ipady=6)
            arena.columnconfigure((0, 2), weight=1)

            tk.Label(
                arena, text="TÚ", bg="white", fg="#777", font=("Arial", 11, "bold")
            ).grid(row=0, column=0)
            tk.Label(
                arena, text="RIVAL", bg="white", fg="#777", font=("Arial", 11, "bold")
            ).grid(row=0, column=2)
            tk.Label(
                arena, text="VS", bg="white", fg="#e8553d", font=("Arial", 20, "bold")
            ).grid(row=1, column=1, padx=10)

            self.mano1 = tk.Label(
                arena, text=EMOJI["piedra"], font=("Arial", 40), bg="white"
            )
            self.mano1.grid(row=1, column=0)
            self.mano2 = tk.Label(
                arena, text=EMOJI["piedra"], font=("Arial", 40), bg="white"
            )
            self.mano2.grid(row=1, column=2)
            fila_r = tk.Frame(self, bg="#f4f1ea")
            fila_r.pack(fill="x", padx=16, pady=(8, 0))
            fila_r.columnconfigure((0, 1), weight=1, uniform="r")
            self.lbl_racha = tk.Label(
                fila_r,
                font=("Arial", 13, "bold"),
                bg="white",
                pady=5,
                highlightbackground="#e2ddd0",
                highlightthickness=1,
            )
            self.lbl_racha.grid(row=0, column=0, padx=5, sticky="ew")
            self.lbl_mult = tk.Label(
                fila_r,
                font=("Arial", 13, "bold"),
                bg="white",
                pady=5,
                highlightbackground="#f2b705",
                highlightthickness=2,
            )
            self.lbl_mult.grid(row=0, column=1, padx=5, sticky="ew")
            self.set_racha(self.racha, self.multiplicador)
            tk.Label(
                self,
                text="Probabilidad del rival",
                font=("Arial", 10, "bold"),
                fg="#777",
                bg="#f4f1ea",
            ).pack(pady=(8, 2))
            fila_p = tk.Frame(self, bg="#f4f1ea")
            fila_p.pack(fill="x", padx=16)
            fila_p.columnconfigure((0, 1, 2), weight=1, uniform="p")
            self.lbl_prob = {}
            for i, nombre in enumerate(("piedra", "papel", "tijera")):
                lbl = tk.Label(
                    fila_p,
                    font=("Arial", 14, "bold"),
                    bg="white",
                    pady=6,
                    highlightbackground="#e2ddd0",
                    highlightthickness=1,
                )
                lbl.grid(row=0, column=i, padx=5, sticky="ew")
                self.lbl_prob[nombre] = lbl
            self.set_probabilidades(self.prob)
            self.lbl_msg = tk.Label(
                self,
                text="¡Elige tu jugada!",
                font=("Arial", 14, "bold"),
                bg="#f4f1ea",
                wraplength=480,  # parte el texto en líneas a partir de 480 px
                height=3,  # reserva siempre 3 líneas de alto
                justify="center",
            )
            self.lbl_msg.pack(pady=6)

            # Botones de jugada
            fila = tk.Frame(self, bg="#f4f1ea")
            fila.pack(fill="x", padx=16)
            fila.columnconfigure((0, 1, 2), weight=1, uniform="a")
            self.botones = []
            for i, nombre in enumerate(("piedra", "papel", "tijera")):
                b = tk.Button(
                    fila,
                    text=f"{EMOJI[nombre]}\n{nombre.capitalize()}",
                    font=("Arial", 14),
                    bg="white",
                    relief="groove",
                    bd=2,
                    command=lambda n=nombre: self.jugar(n),
                )
                b.grid(row=0, column=i, padx=5, sticky="ew")
                self.botones.append(b)

            # Tienda
            tk.Label(
                self, text="🛒 Tienda", font=("Arial", 14, "bold"), bg="#f4f1ea"
            ).pack(anchor="w", padx=16, pady=(20, 0))
            self._fila_tienda(
                "Aumentar probabilidad del rival",
                [
                    ("mas_piedra", "✊⬆️", "Más piedra", preciobs),
                    ("mas_papel", "✋⬆️", "Más papel", preciobs),
                    ("mas_tijera", "✌️⬆️", "Más tijera", preciobs),
                ],
                "#4caf50",
            )
            self._fila_tienda(
                "Reducir probabilidad del rival",
                [
                    ("menos_piedra", "✊⬇️", "Menos piedra", preciobs),
                    ("menos_papel", "✋⬇️", "Menos papel", preciobs),
                    ("menos_tijera", "✌️⬇️", "Menos tijera", preciobs),
                ],
                "#e2ddd0",
            )
            self._fila_tienda(
                "Quitar una baza al rival",
                [
                    ("quitar_piedra", "✊🚫", "Quitar piedra", precioq),
                    ("quitar_papel", "✋🚫", "Quitar papel", precioq),
                    ("quitar_tijera", "✌️🚫", "Quitar tijera", precioq),
                ],
                "#e8553d",
            )
            self.actualizar_tienda()

        def _fila_tienda(self, titulo, items, borde):
            tk.Label(
                self, text=titulo, font=("Arial", 10, "bold"), fg="#777", bg="#f4f1ea"
            ).pack(anchor="w", padx=16, pady=(4, 2))
            fila = tk.Frame(self, bg="#f4f1ea")
            fila.pack(fill="x", padx=16)
            fila.columnconfigure((0, 1, 2), weight=1, uniform="b")
            for i, (clave, icono, nombre, precio) in enumerate(items):
                b = tk.Button(
                    fila,
                    text=f"{icono}\n{nombre}\n🪙 {precio}",
                    font=("Arial", 11),
                    bg="white",
                    highlightbackground=borde,
                    highlightthickness=2,
                    command=lambda c=clave: self.comprar(c),
                )
                self.botones_tienda[clave] = (b, f"{icono}\n{nombre}\n🪙 {precio}")
                b.grid(row=0, column=i, padx=5, sticky="ew")

        # ---------------- FUNCIONES GRÁFICAS (úsalas desde tu lógica) ----------------
        def set_monedas(self, n):
            self.monedas = n
            self.lbl_monedas.config(text=f"🪙 {n}")

        def set_mensaje(self, texto):
            self.lbl_msg.config(text=texto)

        def set_probabilidades(self, prob):
            self.prob = prob
            for nombre, lbl in self.lbl_prob.items():
                probab = prob[nombre]
                if probab <= 0:
                    lbl.config(
                        text=f"{EMOJI[nombre]} ❌", fg="#e8553d"
                    )  # baza eliminada
                else:
                    lbl.config(
                        text=f"{EMOJI[nombre]} {round(probab / 0.9999 * 100, 1)}%",
                        fg="#222",
                    )
            self.actualizar_tienda()

        def set_racha(self, racha, multiplicador):
            self.racha = racha
            self.multiplicador = multiplicador
            self.lbl_racha.config(text=f"🔥 Racha: {racha}")
            self.lbl_mult.config(text=f"✖️ Multiplicador: x{multiplicador:g}")

        def actualizar_tienda(self):
            agotadas = [b for b, p in self.prob.items() if p <= 0]
            tienda_cerrada = len(agotadas) >= 2

            for clave, (boton, texto) in self.botones_tienda.items():
                baza = clave.split("_")[1]
                base = texto.rsplit("\n", 1)[0]  # texto sin la línea del precio
                if tienda_cerrada:
                    boton.config(text=base + "\nCERRADA", state="disabled")
                elif self.prob[baza] <= 0:
                    boton.config(text=base + "\nAGOTADO", state="disabled")
                else:
                    boton.config(text=texto, state="normal")

        def bloquear_botones(self, bloquear):
            for b in self.botones:
                b.config(state="disabled" if bloquear else "normal")

        def animar_enfrentamiento(self, jugador, rival, resultado):
            """resultado: 'gana' | 'pierde' | 'empate'"""
            self.bloquear_botones(True)
            self.set_mensaje("¡Piedra, papel o tijeras!")
            self.mano1.config(text=EMOJI["piedra"], bg="white")
            self.mano2.config(text=EMOJI["piedra"], bg="white")
            self._agitar(0, jugador, rival, resultado)

        def _agitar(self, paso, jugador, rival, resultado):
            if paso < 8:  # el puño sube y baja (3 veces aprox.)
                dy = 18 if paso % 2 == 0 else 0
                self.mano1.grid_configure(pady=(dy, 0))
                self.mano2.grid_configure(pady=(dy, 0))
                self.after(150, self._agitar, paso + 1, jugador, rival, resultado)
            else:
                self.mano1.grid_configure(pady=0)
                self.mano2.grid_configure(pady=0)
                self.mano1.config(text=EMOJI[jugador])
                self.mano2.config(text=EMOJI[rival])
                if resultado == "gana":
                    self.mano1.config(bg="#ffe9a0")
                    self.set_mensaje("🎉 ¡Ganas!")
                elif resultado == "pierde":
                    self.mano2.config(bg="#ffe9a0")
                    self.set_mensaje("😢 Pierdes")
                else:
                    self.set_mensaje("🤝 Empate")
                self.bloquear_botones(False)

        def victoria_final(self):
            self.bloquear_botones(True)
            self.set_mensaje("🏆 ¡RACHA DE 10! ¡HAS GANADO! 🏆")
            self._parpadear(0)

        def _parpadear(self, n):
            if n < 10:
                par = n % 2 == 0
                self.mano1.config(
                    text="🏆" if par else "🎉", bg="#f2b705" if par else "white"
                )
                self.mano2.config(
                    text="🎉" if par else "🏆", bg="#f2b705" if par else "white"
                )
                self.lbl_msg.config(fg="#e8553d" if par else "#222")
                self.after(300, self._parpadear, n + 1)
            else:
                self.reiniciar()

        # ---------------- CREADOR -----------------
        def crear(self):
            conexion(
                """CREATE TABLE TSOPSSB.PPT (
                    PROB_PIEDRA DECIMAL(5, 4),
                    PROB_PAPEL DECIMAL(5, 4),
                    PROB_TIJERA DECIMAL(5, 4),
                    DINERO INT,
                    RACHA INT,
                    MULTIPLICADOR DECIMAL(5, 2))"""
            )

            conexion(
                """INSERT INTO TSOPSSB.PPT (PROB_PIEDRA, PROB_PAPEL, PROB_TIJERA, DINERO, RACHA, MULTIPLICADOR) 
                VALUES (0.3333, 0.3333, 0.3333, 0, 0, 1)"""
            )
            self.select()

        # ----------------- ELIMINADOR -----------------
        def eliminar(self):
            conexion("DROP TABLE TSOPSSB.PPT")

        # ---------------- SELECCIONADOR -----------------
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

        # ---------------- ACTUALIZADOR -----------------
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

        # ---------------- TU LÓGICA AQUÍ ----------------
        def mostrar_stats(self):
            self.set_monedas(self.monedas)
            self.set_racha(self.racha, self.multiplicador)
            if self.racha >= 10:
                self.after(100, self.victoria_final)

        def reiniciar(self):
            self.eliminar()
            self.crear()
            self.set_monedas(self.monedas)
            self.set_racha(self.racha, self.multiplicador)
            self.set_probabilidades(self.prob)  # esta también actualiza la tienda
            self.mano1.config(text=EMOJI["piedra"], bg="white")
            self.mano2.config(text=EMOJI["piedra"], bg="white")
            self.lbl_msg.config(fg="#222")
            self.set_mensaje("¡Elige tu jugada!")
            self.bloquear_botones(False)

        def jugar(self, eleccion):
            rival, resultado = juego_ppt(eleccion)
            self.select()
            self.animar_enfrentamiento(eleccion, rival, resultado)
            if resultado == "pierde":
                self.monedas = max(self.monedas - perdida, 0)
                self.racha = 0
                self.multiplicador = 1
            elif resultado == "gana":
                self.monedas = int(
                    round(self.monedas + ganancia * self.multiplicador, 0)
                )
                self.racha += 1
                if basepot == 0:
                    self.multiplicador = 1 + self.racha * aumentomult
                else:
                    self.multiplicador = basepot ** (self.racha * aumentomult)
            else:
                self.racha = 0
                self.multiplicador = 1
            self.updatear()
            self.after(1250, self.mostrar_stats)

        def comprar(self, item):
            self.select()
            agotadas = [baza for baza, probab in self.prob.items() if probab == 0]
            if len(agotadas) == 2:
                self.set_mensaje(
                    "No puedes comprar nada. Solo le queda una baza al rival."
                )
                return
            if item == "mas_piedra":
                if self.monedas < preciobs:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["piedra"] == 1:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar piedra ya era 1."
                    )
                    return
                self.set_mensaje(
                    "La probabilidad de que el rival saque piedra ha aumentado."
                )
                self.set_monedas(self.monedas - preciobs)
                if len(agotadas) == 1:
                    self.prob["piedra"] = min(1, self.prob["piedra"] + 0.02)
                    restante = next(
                        b for b in self.prob if b not in ("piedra", agotadas[0])
                    )
                    self.prob[restante] = max(0, self.prob[restante] - 0.02)
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                if self.prob["piedra"] > 0.98:
                    self.prob["papel"] = 0
                    self.prob["tijera"] = 0
                    self.prob["piedra"] = 1
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                self.prob["piedra"] = min(1, self.prob["piedra"] + 0.02)
                self.prob["papel"] = max(0, self.prob["papel"] - 0.01)
                self.prob["tijera"] = max(0, self.prob["tijera"] - 0.01)
                self.set_probabilidades(self.prob)
            if item == "mas_papel":
                if self.monedas < preciobs:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["papel"] == 1:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar papel ya era 1."
                    )
                    return
                self.set_mensaje(
                    "La probabilidad de que el rival saque papel ha aumentado."
                )
                self.set_monedas(self.monedas - preciobs)
                if len(agotadas) == 1:
                    self.prob["papel"] = min(1, self.prob["papel"] + 0.02)
                    restante = next(
                        b for b in self.prob if b not in ("papel", agotadas[0])
                    )
                    self.prob[restante] = max(0, self.prob[restante] - 0.02)
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                if self.prob["papel"] > 0.98:
                    self.prob["piedra"] = 0
                    self.prob["tijera"] = 0
                    self.prob["papel"] = 1
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                self.prob["papel"] = min(1, self.prob["papel"] + 0.02)
                self.prob["piedra"] = max(0, self.prob["piedra"] - 0.01)
                self.prob["tijera"] = max(0, self.prob["tijera"] - 0.01)
                self.set_probabilidades(self.prob)
            if item == "mas_tijera":
                if self.monedas < preciobs:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["tijera"] == 1:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar tijera ya era 1."
                    )
                    return
                self.set_mensaje(
                    "La probabilidad de que el rival saque tijera ha aumentado."
                )
                self.set_monedas(self.monedas - preciobs)
                if len(agotadas) == 1:
                    self.prob["tijera"] = min(1, self.prob["tijera"] + 0.02)
                    restante = next(
                        b for b in self.prob if b not in ("tijera", agotadas[0])
                    )
                    self.prob[restante] = max(0, self.prob[restante] - 0.02)
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                if self.prob["tijera"] > 0.98:
                    self.prob["piedra"] = 0
                    self.prob["papel"] = 0
                    self.prob["tijera"] = 1
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                self.prob["tijera"] = min(1, self.prob["tijera"] + 0.02)
                self.prob["piedra"] = max(0, self.prob["piedra"] - 0.01)
                self.prob["papel"] = max(0, self.prob["papel"] - 0.01)
                self.set_probabilidades(self.prob)
            if item == "menos_piedra":
                if self.monedas < preciobs:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["piedra"] == 0:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar piedra ya era cero."
                    )
                    return
                self.set_mensaje(
                    "La probabilidad de que el rival saque piedra ha disminuido."
                )
                self.set_monedas(self.monedas - preciobs)
                if len(agotadas) == 1:
                    self.prob["piedra"] = max(0, self.prob["piedra"] - 0.02)
                    restante = next(
                        b for b in self.prob if b not in ("piedra", agotadas[0])
                    )
                    self.prob[restante] = min(1, self.prob[restante] + 0.02)
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                if self.prob["piedra"] < 0.02:
                    self.prob["papel"] = (
                        self.prob["papel"] + (self.prob["piedra"] / 2)
                    ) / 0.9999
                    self.prob["tijera"] = (
                        self.prob["tijera"] + (self.prob["piedra"] / 2)
                    ) / 0.9999
                    self.prob["piedra"] = 0
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                self.prob["piedra"] = max(0, self.prob["piedra"] - 0.02)
                self.prob["papel"] = min(1, self.prob["papel"] + 0.01)
                self.prob["tijera"] = min(1, self.prob["tijera"] + 0.01)
                self.set_probabilidades(self.prob)
            if item == "menos_papel":
                if self.monedas < preciobs:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["papel"] == 0:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar papel ya era cero."
                    )
                    return
                self.set_mensaje(
                    "La probabilidad de que el rival saque papel ha disminuido."
                )
                self.set_monedas(self.monedas - preciobs)
                if len(agotadas) == 1:
                    self.prob["papel"] = max(0, self.prob["papel"] - 0.02)
                    restante = next(
                        b for b in self.prob if b not in ("papel", agotadas[0])
                    )
                    self.prob[restante] = min(1, self.prob[restante] + 0.02)
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                if self.prob["papel"] < 0.02:
                    self.prob["piedra"] = (
                        self.prob["piedra"] + (self.prob["papel"] / 2)
                    ) / 0.9999
                    self.prob["tijera"] = (
                        self.prob["tijera"] + (self.prob["papel"] / 2)
                    ) / 0.9999
                    self.prob["papel"] = 0
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                self.prob["papel"] = max(0, self.prob["papel"] - 0.02)
                self.prob["piedra"] = min(1, self.prob["piedra"] + 0.01)
                self.prob["tijera"] = min(1, self.prob["tijera"] + 0.01)
                self.set_probabilidades(self.prob)
            if item == "menos_tijera":
                if self.monedas < preciobs:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["tijera"] == 0:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar tijera ya era cero."
                    )
                    return
                self.set_mensaje(
                    "La probabilidad de que el rival saque tijera ha disminuido."
                )
                self.set_monedas(self.monedas - preciobs)
                if len(agotadas) == 1:
                    self.prob["tijera"] = max(0, self.prob["tijera"] - 0.02)
                    restante = next(
                        b for b in self.prob if b not in ("tijera", agotadas[0])
                    )
                    self.prob[restante] = min(1, self.prob[restante] + 0.02)
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                if self.prob["tijera"] < 0.02:
                    self.prob["piedra"] = (
                        self.prob["piedra"] + (self.prob["tijera"] / 2)
                    ) / 0.9999
                    self.prob["papel"] = (
                        self.prob["papel"] + (self.prob["tijera"] / 2)
                    ) / 0.9999
                    self.prob["tijera"] = 0
                    self.set_probabilidades(self.prob)
                    self.updatear()
                    return
                self.prob["tijera"] = max(0, self.prob["tijera"] - 0.02)
                self.prob["piedra"] = min(1, self.prob["piedra"] + 0.01)
                self.prob["papel"] = min(1, self.prob["papel"] + 0.01)
                self.set_probabilidades(self.prob)
            if item == "quitar_piedra":
                if self.monedas < precioq:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["piedra"] == 0:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar piedra ya era cero."
                    )
                    return
                self.set_mensaje("El rival ya no puede sacar piedra.")
                self.set_monedas(self.monedas - precioq)
                p, t = self.prob["papel"], self.prob["tijera"]
                self.prob["piedra"] = 0
                self.prob["papel"] = p / (p + t)
                self.prob["tijera"] = t / (p + t)
                self.set_probabilidades(self.prob)
            if item == "quitar_papel":
                if self.monedas < precioq:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["papel"] == 0:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar papel ya era cero."
                    )
                    return
                self.set_mensaje("El rival ya no puede sacar papel.")
                self.set_monedas(self.monedas - precioq)
                p, t = self.prob["piedra"], self.prob["tijera"]
                self.prob["piedra"] = p / (p + t)
                self.prob["papel"] = 0
                self.prob["tijera"] = t / (p + t)
                self.set_probabilidades(self.prob)
            if item == "quitar_tijera":
                if self.monedas < precioq:
                    self.set_mensaje("No tienes suficientes monedas para comprar.")
                    return
                if self.prob["tijera"] == 0:
                    self.set_mensaje(
                        "No se han gastado monedas. La probabilidad de sacar tijera ya era cero."
                    )
                    return
                self.set_mensaje("El rival ya no puede sacar tijera.")
                self.set_monedas(self.monedas - precioq)
                pi, pa = self.prob["piedra"], self.prob["papel"]
                self.prob["piedra"] = pi / (pi + pa)
                self.prob["papel"] = pa / (pi + pa)
                self.prob["tijera"] = 0
                self.set_probabilidades(self.prob)
            self.updatear()

    Juego().mainloop()

import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd

# Integração do Matplotlib com Tkinter para gráficos no Dashboard
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# CustomTkinter para estilo visual moderno
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    BaseWindow = ctk.CTk
except ImportError:
    BaseWindow = tk.Tk


class DashboardScreenerApp(BaseWindow):

    def __init__(self):
        super().__init__()

        self.title("Dashboard Fundamentalista B3 - Screener & Analytics")
        self.geometry("1380x820")

        # Paleta de Cores Dark Mode
        self.BG_COLOR = "#1e1e1e"
        self.CARD_BG = "#252526"
        self.ACCENT_COLOR = "#007acc"
        self.GREEN_COLOR = "#4ec9b0"
        self.YELLOW_COLOR = "#cca700"
        self.TEXT_MAIN = "#ffffff"
        self.TEXT_MUTED = "#a0a0a0"

        self.df_raw = None
        self.df_processed = None

        self._aplicar_cabecalho_escuro()
        self._configurar_estilos()
        self._criar_interface()

    def _aplicar_cabecalho_escuro(self):
        try:
            self.update()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:
            pass

    def _configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("Card.TFrame", background=self.CARD_BG)
        style.configure("TNotebook", background=self.BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d", foreground="#ffffff", padding=[15, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.ACCENT_COLOR)], foreground=[("selected", "#ffffff")])

        # Tabela (Treeview)
        style.configure(
            "Treeview",
            background="#2d2d2d",
            foreground="#ffffff",
            fieldbackground="#2d2d2d",
            rowheight=26,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#1f1f1f",
            foreground=self.ACCENT_COLOR,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", self.ACCENT_COLOR)], foreground=[("selected", "#ffffff")])

    def _criar_interface(self):
        # 1. BARRA SUPERIOR DE CONTROLE E FILTROS
        top_frame = ttk.Frame(self, style="Card.TFrame", padding=12)
        top_frame.pack(fill="x", padx=15, pady=(15, 5))

        btn_carregar = tk.Button(
            top_frame, text="📁 Abrir CSV StatusInvest", command=self.carregar_csv,
            bg=self.ACCENT_COLOR, fg="white", font=("Segoe UI", 10, "bold"),
            padx=12, pady=5, relief="flat", cursor="hand2"
        )
        btn_carregar.pack(side="left", padx=(0, 15))

        tk.Label(top_frame, text="Estratégia:", bg=self.CARD_BG, fg=self.TEXT_MAIN, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(5, 5))

        self.combo_presets = ttk.Combobox(
            top_frame,
            values=[
                "Todas as Ações",
                "⭐ Top Score Fundamentalista",
                "💰 Método Bazin (Proventos + Preço Teto)",
                "🛡️ Método Graham (Ações Baratas P/L + P/VP)",
                "🧙‍♂️ Magic Formula (Greenblatt - EV/EBIT + ROIC)",
            ],
            width=40, state="readonly"
        )
        self.combo_presets.current(0)
        self.combo_presets.pack(side="left", padx=5)
        self.combo_presets.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        tk.Label(top_frame, text="Liq. Mín. (R$):", bg=self.CARD_BG, fg=self.TEXT_MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(15, 5))
        self.entry_liq = tk.Entry(top_frame, bg="#1e1e1e", fg="white", insertbackground="white", width=12)
        self.entry_liq.insert(0, "200000")
        self.entry_liq.pack(side="left", padx=5)

        btn_refiltrar = tk.Button(top_frame, text="Filtrar", command=self.aplicar_filtros, bg="#333333", fg="white", relief="flat")
        btn_refiltrar.pack(side="left", padx=5)

        self.lbl_info = tk.Label(top_frame, text="Aguardando CSV...", bg=self.CARD_BG, fg=self.GREEN_COLOR, font=("Segoe UI", 9, "bold"))
        self.lbl_info.pack(side="right", padx=10)

        # 2. SISTEMA DE ABAS (NOTEBOOK)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=5)

        self.tab_screener = ttk.Frame(self.notebook)
        self.tab_analytics = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_screener, text="📊 Screener & Raio-X")
        self.notebook.add(self.tab_analytics, text="📈 Dashboard & Gráficos")

        self._montar_aba_screener()
        self._montar_aba_analytics()

    def _montar_aba_screener(self):
        # Usando ttk.PanedWindow para aceitar a opção weight=...
        paned = ttk.PanedWindow(self.tab_screener, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # LADO ESQUERDO: TABELA DE AÇÕES
        left_frame = ttk.Frame(paned, style="TFrame")
        paned.add(left_frame, weight=3)

        cols = ["TICKER", "SCORE", "PRECO", "DY", "P/L", "P/VP", "EV/EBIT", "ROE", "ROIC", "MARG. LIQUIDA"]
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")

        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        larguras = {"TICKER": 75, "SCORE": 65, "PRECO": 70, "DY": 65, "P/L": 65, "P/VP": 65, "EV/EBIT": 70, "ROE": 65, "ROIC": 65, "MARG. LIQUIDA": 95}
        for col in cols:
            self.tree.heading(col, text=col, command=lambda _col=col: self._ordenar_coluna(_col, False))
            self.tree.column(col, width=larguras.get(col, 80), anchor="center" if col in ["TICKER", "SCORE"] else "e")

        self.tree.bind("<<TreeviewSelect>>", self._on_select_acao)

        # LADO DIREITO: CARD RAIO-X DETALHADO
        right_card = ttk.Frame(paned, style="Card.TFrame", padding=15)
        paned.add(right_card, weight=1)

        tk.Label(right_card, text="🔍 RAIO-X DA AÇÃO", bg=self.CARD_BG, fg=self.TEXT_MAIN, font=("Segoe UI", 11, "bold")).pack(fill="x", pady=(0, 10))

        self.lbl_raio_ticker = tk.Label(right_card, text="Selecione uma Ação", bg=self.CARD_BG, fg=self.ACCENT_COLOR, font=("Segoe UI", 16, "bold"))
        self.lbl_raio_ticker.pack(fill="x")

        self.lbl_raio_preco = tk.Label(right_card, text="--", bg=self.CARD_BG, fg=self.GREEN_COLOR, font=("Segoe UI", 12, "bold"))
        self.lbl_raio_preco.pack(fill="x", pady=(0, 15))

        ttk.Separator(right_card, orient="horizontal").pack(fill="x", pady=5)

        self.lbl_detalhes_text = tk.Text(
            right_card, bg="#1e1e1e", fg="white", font=("Consolas", 9),
            relief="flat", height=20, wrap="word"
        )
        self.lbl_detalhes_text.pack(fill="both", expand=True, pady=10)

    def _montar_aba_analytics(self):
        # Frame superior para KPIs Rápidos
        self.kpi_frame = ttk.Frame(self.tab_analytics, style="Card.TFrame", padding=10)
        self.kpi_frame.pack(fill="x", pady=(0, 10))

        self.lbl_kpi_total = self._criar_card_kpi(self.kpi_frame, "Total Filtradas", "--", 0)
        self.lbl_kpi_score = self._criar_card_kpi(self.kpi_frame, "Média Score", "--", 1)
        self.lbl_kpi_dy = self._criar_card_kpi(self.kpi_frame, "Média DY %", "--", 2)
        self.lbl_kpi_pl = self._criar_card_kpi(self.kpi_frame, "Média P/L", "--", 3)

        # Container dos Gráficos Matplotlib
        self.chart_container = ttk.Frame(self.tab_analytics, style="TFrame")
        self.chart_container.pack(fill="both", expand=True)

    def _criar_card_kpi(self, parent, titulo, valor_init, col):
        card = ttk.Frame(parent, style="TFrame", padding=10)
        card.grid(row=0, column=col, sticky="nsew", padx=10)
        parent.columnconfigure(col, weight=1)

        tk.Label(card, text=titulo, bg=self.BG_COLOR, fg=self.TEXT_MUTED, font=("Segoe UI", 8)).pack()
        lbl_val = tk.Label(card, text=valor_init, bg=self.BG_COLOR, fg=self.GREEN_COLOR, font=("Segoe UI", 12, "bold"))
        lbl_val.pack()
        return lbl_val

    def _tratar_valores_numericos(self, df):
        df.columns = df.columns.str.strip()
        def clean_num(val):
            if pd.isna(val): return None
            val_str = str(val).strip().replace('.', '').replace(',', '.')
            try: return float(val_str)
            except ValueError: return None

        for col in [c for c in df.columns if c != "TICKER"]:
            df[col] = df[col].apply(clean_num)
        return df

    def _calcular_indicadores_avancados(self, df):
        # Graham: sqrt(22.5 * LPA * VPA)
        df["GRAHAM (VI)"] = df.apply(
            lambda r: (22.5 * r["LPA"] * r["VPA"])**0.5 if pd.notna(r.get("LPA")) and pd.notna(r.get("VPA")) and r["LPA"]>0 and r["VPA"]>0 else None, axis=1
        )
        # Bazin: DPA / 0.06
        df["BAZIN (VI)"] = df.apply(
            lambda r: (r["PRECO"] * (r["DY"] / 100.0)) / 0.06 if pd.notna(r.get("PRECO")) and pd.notna(r.get("DY")) and r["DY"]>0 else None, axis=1
        )

        # Score Fundamentalista 0 a 100
        def calc_score(r):
            s = 0
            s += 15 if (r.get("DY") or 0) >= 6.0 else (8 if (r.get("DY") or 0) >= 3.0 else 0)
            s += 15 if (r.get("ROE") or 0) >= 15 else (8 if (r.get("ROE") or 0) >= 10 else 0)
            s += 10 if (r.get("ROIC") or 0) >= 12 else (5 if (r.get("ROIC") or 0) >= 8 else 0)
            pl = r.get("P/L") or 999
            pvp = r.get("P/VP") or 999
            s += 15 if 0 < pl <= 10 else (8 if 10 < pl <= 15 else 0)
            s += 10 if 0 < pvp <= 1.5 else (5 if 1.5 < pvp <= 2.5 else 0)
            s += 15 if (r.get("MARG. LIQUIDA") or 0) >= 15 else (8 if (r.get("MARG. LIQUIDA") or 0) >= 8 else 0)
            d_ebit = r.get("DIVIDA LIQUIDA / EBIT")
            if pd.notna(d_ebit):
                s += 20 if d_ebit <= 2.0 else (10 if d_ebit <= 3.5 else 0)
            return s

        df["SCORE"] = df.apply(calc_score, axis=1)

        # Magic Formula Rank
        df_mf = df[(df["EV/EBIT"] > 0) & (df["ROIC"] > 0) & (df["LIQUIDEZ MEDIA DIARIA"] >= 100000)].copy()
        if not df_mf.empty:
            df_mf["MAGIC_SCORE"] = df_mf["EV/EBIT"].rank(ascending=True) + df_mf["ROIC"].rank(ascending=False)
            df["MAGIC_SCORE"] = df_mf["MAGIC_SCORE"]
        else:
            df["MAGIC_SCORE"] = 9999

        return df

    def carregar_csv(self):
        caminho = filedialog.askopenfilename(filetypes=[("Arquivos CSV", "*.csv"), ("Todos", "*.*")])
        if not caminho: return

        try:
            try: df = pd.read_csv(caminho, sep=";", encoding="utf-8")
            except Exception: df = pd.read_csv(caminho, sep=";", encoding="latin1")

            df = self._tratar_valores_numericos(df)
            self.df_raw = self._calcular_indicadores_avancados(df)
            self.lbl_info.config(text=f"{len(self.df_raw)} ações na base.")
            self.aplicar_filtros()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao ler CSV:\n{str(e)}")

    def aplicar_filtros(self, event=None):
        if self.df_raw is None: return

        try: liq_min = float(self.entry_liq.get().replace(".", ""))
        except ValueError: liq_min = 200000.0

        df = self.df_raw[self.df_raw["LIQUIDEZ MEDIA DIARIA"].fillna(0) >= liq_min].copy()
        preset = self.combo_presets.get()

        if "Top Score" in preset: df = df.sort_values(by="SCORE", ascending=False)
        elif "Bazin" in preset: df = df[(df["DY"] >= 6.0) & (df["PRECO"] <= df["BAZIN (VI)"])].sort_values(by="DY", ascending=False)
        elif "Graham" in preset: df = df[(df["P/L"] > 0) & (df["P/L"] <= 15) & (df["P/VP"] <= 1.5)].sort_values(by="SCORE", ascending=False)
        elif "Magic Formula" in preset: df = df[df["MAGIC_SCORE"] < 9000].sort_values(by="MAGIC_SCORE", ascending=True)
        else: df = df.sort_values(by="SCORE", ascending=False)

        self.df_processed = df
        self._preencher_tabela(df)
        self._atualizar_dashboard(df)

    def _preencher_tabela(self, df):
        for item in self.tree.get_children(): self.tree.delete(item)
        cols = ["TICKER", "SCORE", "PRECO", "DY", "P/L", "P/VP", "EV/EBIT", "ROE", "ROIC", "MARG. LIQUIDA"]

        for _, row in df.iterrows():
            vals = []
            for c in cols:
                v = row.get(c)
                if pd.isna(v) or v is None: vals.append("--")
                elif c == "TICKER": vals.append(str(v))
                elif c == "SCORE": vals.append(f"{int(v)} pts")
                elif c == "PRECO": vals.append(f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                else: vals.append(f"{v:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."))
            self.tree.insert("", "end", values=vals)

    def _ordenar_coluna(self, col, reverse):
        if self.df_processed is None or self.df_processed.empty: return
        
        col_map = {"DIV. LIQ. / EBIT": "DIVIDA LIQUIDA / EBIT"}
        col_db = col_map.get(col, col)

        if col_db in self.df_processed.columns:
            self.df_processed = self.df_processed.sort_values(by=col_db, ascending=reverse, na_position="last")
            self._preencher_tabela(self.df_processed)
            self.tree.heading(col, command=lambda: self._ordenar_coluna(col, not reverse))

    def _on_select_acao(self, event):
        sel = self.tree.selection()
        if not sel or self.df_processed is None: return

        item = self.tree.item(sel[0])
        ticker = item["values"][0]

        row = self.df_processed[self.df_processed["TICKER"] == ticker].iloc[0]

        self.lbl_raio_ticker.config(text=ticker)
        self.lbl_raio_preco.config(text=f"R$ {row['PRECO']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Texto detalhado do Raio-X
        self.lbl_detalhes_text.delete("1.0", tk.END)
        info = f"""---------------------------------
📊 DESTAQUES DE VALUATION:
---------------------------------
• Score Geral: {row['SCORE']} / 100
• P/L: {row.get('P/L', '--')}
• P/VP: {row.get('P/VP', '--')}
• EV/EBIT: {row.get('EV/EBIT', '--')}

💵 PROVENTOS & MARGENS:
• Dividend Yield: {row.get('DY', '--')}%
• Margem Líquida: {row.get('MARG. LIQUIDA', '--')}%
• ROE: {row.get('ROE', '--')}% | ROIC: {row.get('ROIC', '--')}%

🎯 PREÇOS TETO E INTRÍNSECOS:
• Preço Intrínseco (Graham): R$ {row.get('GRAHAM (VI)', 0):,.2f}
• Preço Teto (Bazin 6%): R$ {row.get('BAZIN (VI)', 0):,.2f}

⚠️ SAÚDE FINANCEIRA:
• Dívida Líq./EBIT: {row.get('DIVIDA LIQUIDA / EBIT', '--')}
• Liquidez Diária: R$ {row.get('LIQUIDEZ MEDIA DIARIA', 0):,.0f}
"""
        self.lbl_detalhes_text.insert(tk.END, info)

    def _atualizar_dashboard(self, df):
        if df.empty: return

        self.lbl_kpi_total.config(text=str(len(df)))
        self.lbl_kpi_score.config(text=f"{df['SCORE'].mean():.1f} pts")
        self.lbl_kpi_dy.config(text=f"{df['DY'].mean():.2f}%")
        self.lbl_kpi_pl.config(text=f"{df['P/L'].mean():.2f}")

        for widget in self.chart_container.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(10, 4), facecolor="#1e1e1e")

        # Gráfico 1: Top 10 Maior Score
        ax1 = fig.add_subplot(121)
        top10_score = df.head(10)
        ax1.set_facecolor("#252526")
        ax1.barh(top10_score["TICKER"], top10_score["SCORE"], color="#007acc")
        ax1.invert_yaxis()
        ax1.set_title("Top 10 - Score Fundamentalista", color="white", fontsize=10, fontweight="bold")
        ax1.tick_params(colors="white", labelsize=8)

        # Gráfico 2: Dispersão ROIC vs EV/EBIT
        ax2 = fig.add_subplot(122)
        ax2.set_facecolor("#252526")
        df_disp = df[(df["EV/EBIT"] > 0) & (df["EV/EBIT"] < 30) & (df["ROIC"] < 50)]
        ax2.scatter(df_disp["EV/EBIT"], df_disp["ROIC"], color="#4ec9b0", alpha=0.7)
        ax2.set_title("Eficiência (ROIC %) vs Valuation (EV/EBIT)", color="white", fontsize=10, fontweight="bold")
        ax2.set_xlabel("EV/EBIT", color="white", fontsize=8)
        ax2.set_ylabel("ROIC %", color="white", fontsize=8)
        ax2.tick_params(colors="white", labelsize=8)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    app = DashboardScreenerApp()
    app.mainloop()
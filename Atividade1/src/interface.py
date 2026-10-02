# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Módulo de Interface Gráfica (Tkinter).

Implementa a interface visual completa do software da Camada Física Acústica:
- Seleção de Método:
  * Método 1: Batidas por Impacto (Paridade Par, quadros de 9 bits)
  * Método 2: Modulação FSK Contínua 1200/2200 Hz (CRC-8 padrão ATM 0x07)
- Seleção de Papel:
  * Transmissor (TX)
  * Receptor (RX)
  * Transceptor Completo (TX e RX na mesma tela para testes no mesmo PC)
- Para o Método 1:
  * Transmissor: digitação de mensagem, codificação em quadros de 9 bits (8 dados + 1 paridade par),
    exibição completa dos bits, botão para reproduzir batidas no alto-falante,
    opção de injeção de erro de paridade e guia visual para batidas manuais.
  * Receptor: escuta do microfone em tempo real, detecção de 1 batida (0) e 2 batidas (1),
    montagem de quadros de 9 bits, validação de paridade, reconstrução de mensagem
    em modo autônomo (sem mensagem prévia) ou com mensagem de referência opcional,
    calibração de ruído ambiente e controle de sensibilidade.
- Para o Método 2:
  * Transmissor: Entrada A (texto automático com CRC-8 e transmissão FSK pelo alto-falante)
    e Entrada B (entrada manual por impactos: palmas/batidas no microfone -> bits -> FSK -> alto-falante).
  * Receptor: captura pelo microfone, detecção de preâmbulo via filtro casado,
    demodulação espectral por DFT, validação de integridade CRC-8 e reconstrução de mensagem.
"""

import sys
import threading
from typing import Dict, Any, List, Optional
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

from .conversao import (
    mensagem_para_bits,
    bits_para_mensagem,
    formatar_bits,
    bits_para_bytes,
    bytes_para_bits,
)
from .deteccao_erros import (
    calcular_bit_paridade_par,
    criar_quadro_metodo1,
    verificar_quadro_metodo1,
    codificar_mensagem_metodo1,
    decodificar_quadros_metodo1,
    calcular_crc8,
    montar_pacote_metodo2,
    desmontar_pacote_metodo2,
    codificar_mensagem_metodo2,
    decodificar_bits_metodo2,
    injetar_erro_de_bit,
)
from .metodo1_batidas.transmissor import (
    sintetizar_bits_metodo1,
    transmitir_audio_metodo1,
    parar_transmissao_metodo1,
)
from .metodo1_batidas.receptor import (
    DetectorBatidasTempoReal,
    decodificar_audio_metodo1,
    gravar_audio_microfone,
)
from .metodo2_fsk.transmissor import (
    sintetizar_bits_fsk,
    transmitir_audio_fsk,
    parar_transmissao_fsk,
    calcular_taxa_bps,
    FREQ_BIT_0,
    FREQ_BIT_1,
    FREQ_PREAMBULO,
)
from .metodo2_fsk.receptor import (
    decodificar_audio_fsk,
    gravar_audio_microfone_fsk,
)


class AppCamadaFisica(tk.Tk):
    """Janela principal da aplicação de Camada Física usando Som."""

    def __init__(self):
        super().__init__()
        self.title("Camada Física usando Som - Redes de Computadores")
        self.geometry("1020x860")
        self.minsize(920, 740)

        # Variáveis de Estado Principais
        self.var_metodo = tk.StringVar(value="metodo1")      # 'metodo1' ou 'metodo2'
        self.var_papel = tk.StringVar(value="tx")            # 'tx', 'rx' ou 'ambos'
        self.var_modo_entrada_m2 = tk.StringVar(value="auto") # 'auto' (texto) ou 'impacto' (batidas)

        # Variáveis do Transmissor (TX)
        self.var_mensagem_tx = tk.StringVar(value="OI")
        self.var_injetar_erro_m1 = tk.BooleanVar(value=False)
        self.var_injetar_erro_m2 = tk.BooleanVar(value=False)
        self.transmitindo_m1 = False
        self.transmitindo_m2 = False

        # Variáveis do Receptor (RX)
        self.var_msg_ref_rx = tk.StringVar(value="")
        self.var_limiar = tk.DoubleVar(value=0.08)
        self.var_modo_teste_m1 = tk.BooleanVar(value=False)
        self.var_duracao_fsk = tk.DoubleVar(value=6.0)

        # Estado da Recepção em Tempo Real (Método 1)
        self.escutando_tempo_real_m1 = False
        self.bits_recebidos_m1: List[int] = []
        self.mensagem_reconstruida_m1 = ""
        self.total_batidas_m1 = 0

        # Estado da Entrada Manual por Batidas no Método 2 TX
        self.escutando_impactos_m2_tx = False
        self.bits_impactos_m2_tx: List[int] = []

        # Histórico de sinais gerados
        self.ultimo_audio_fsk: Optional[np.ndarray] = None
        self.ultimos_bits_fsk: List[int] = []

        # Instâncias de Detectores de Batidas em Tempo Real
        self.detector_m1 = DetectorBatidasTempoReal(
            callback_bit=self._ao_receber_bit_m1,
            callback_evento=self._ao_receber_evento_m1,
            limiar=self.var_limiar.get(),
            debounce_s=0.085,
            janela_dupla_s=0.35,
        )

        self.detector_m2_impactos = DetectorBatidasTempoReal(
            callback_bit=self._ao_receber_bit_m2_tx,
            callback_evento=self._ao_receber_evento_m2_tx,
            limiar=self.var_limiar.get(),
            debounce_s=0.085,
            janela_dupla_s=0.35,
        )

        self._construir_layout()
        self._configurar_rastreamento()
        self._atualizar_visibilidade_paineis()
        self._atualizar_detalhes_tx_m1()
        self._atualizar_detalhes_tx_m2()

        # Encerramento gracioso ao fechar
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    def _ao_fechar(self):
        if self.detector_m1.ativo:
            self.detector_m1.parar()
        if self.detector_m2_impactos.ativo:
            self.detector_m2_impactos.parar()
        parar_transmissao_metodo1()
        parar_transmissao_fsk()
        self.destroy()

    def _configurar_rastreamento(self):
        self.var_mensagem_tx.trace_add("write", lambda *_: self._ao_alterar_mensagem_tx())
        self.var_msg_ref_rx.trace_add("write", lambda *_: self._ao_alterar_ref_rx())
        self.var_limiar.trace_add("write", lambda *_: self._ao_alterar_limiar())
        self.var_injetar_erro_m1.trace_add("write", lambda *_: self._atualizar_detalhes_tx_m1())
        self.var_injetar_erro_m2.trace_add("write", lambda *_: self._atualizar_detalhes_tx_m2())

    def _ao_alterar_mensagem_tx(self):
        self._atualizar_detalhes_tx_m1()
        self._atualizar_detalhes_tx_m2()

    def _ao_alterar_ref_rx(self):
        ref = self.var_msg_ref_rx.get().strip()
        if ref:
            bits_ref = codificar_mensagem_metodo1(mensagem_para_bits(ref))
            self.lbl_ref_bits_info.config(
                text=f"Referência: '{ref}' -> {len(bits_ref)} bits esperados: {''.join(str(b) for b in bits_ref)}"
            )
        else:
            self.lbl_ref_bits_info.config(
                text="Recepção Livre: Nenhuma mensagem pré-definida. O receptor decodifica qualquer áudio capturado!"
            )

    def _ao_alterar_limiar(self):
        val = self.var_limiar.get()
        self.detector_m1.definir_limiar(val)
        self.detector_m2_impactos.definir_limiar(val)
        self.lbl_limiar_val.config(text=f"{val:.3f}")

    # ==========================================================================
    # CONSTRUÇÃO DO LAYOUT
    # ==========================================================================
    def _construir_layout(self):
        # 1. Cabeçalho Superior
        frame_header = tk.Frame(self, bg="#0f172a", padx=16, pady=10)
        frame_header.pack(fill=tk.X)

        lbl_titulo = tk.Label(
            frame_header,
            text="CAMADA FÍSICA ACÚSTICA - REDES DE COMPUTADORES",
            font=("Arial", 13, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
        )
        lbl_titulo.pack(anchor="w")

        lbl_sub = tk.Label(
            frame_header,
            text="Comunicação por Áudio Real: Alto-falante → Ambiente → Microfone (Dois Métodos Independentes)",
            font=("Arial", 9),
            fg="#94a3b8",
            bg="#0f172a",
        )
        lbl_sub.pack(anchor="w")

        # Container Principal
        self.container = ttk.Frame(self, padding="10")
        self.container.pack(fill=tk.BOTH, expand=True)

        # 2. Painel de Seleção de Método e Papel
        frame_topo = ttk.LabelFrame(self.container, text=" 1. Configuração de Operação ", padding="8")
        frame_topo.pack(fill=tk.X, pady=(0, 6))

        # Linha Método
        f_metodo = ttk.Frame(frame_topo)
        f_metodo.pack(fill=tk.X, pady=2)
        ttk.Label(f_metodo, text="Método:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            f_metodo,
            text="Método 1 — Batidas por Impacto (Paridade Par, 9 bits)",
            variable=self.var_metodo,
            value="metodo1",
            command=self._ao_trocar_metodo,
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            f_metodo,
            text="Método 2 — Modulação FSK Contínua 1200/2200 Hz (CRC-8)",
            variable=self.var_metodo,
            value="metodo2",
            command=self._ao_trocar_metodo,
        ).pack(side=tk.LEFT)

        # Linha Papel
        f_papel = ttk.Frame(frame_topo)
        f_papel.pack(fill=tk.X, pady=2)
        ttk.Label(f_papel, text="Papel:  ", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            f_papel,
            text="Transmissor (TX)",
            variable=self.var_papel,
            value="tx",
            command=self._ao_trocar_papel,
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            f_papel,
            text="Receptor (RX)",
            variable=self.var_papel,
            value="rx",
            command=self._ao_trocar_papel,
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            f_papel,
            text="Transceptor Completo (TX e RX juntos no mesmo computador)",
            variable=self.var_papel,
            value="ambos",
            command=self._ao_trocar_papel,
        ).pack(side=tk.LEFT)

        # 3. Painel Dinâmico Central (Frames de TX e RX dos Métodos)
        self.frame_conteudo = ttk.Frame(self.container)
        self.frame_conteudo.pack(fill=tk.BOTH, expand=False, pady=(0, 6))

        # --- A) MÉTODO 1 - TRANSMISSOR ---
        self.frame_m1_tx = ttk.LabelFrame(
            self.frame_conteudo, text=" 2. Transmissor — Método 1 (Batidas por Impacto) ", padding="8"
        )
        self._construir_m1_tx()

        # --- B) MÉTODO 1 - RECEPTOR ---
        self.frame_m1_rx = ttk.LabelFrame(
            self.frame_conteudo, text=" 3. Receptor — Método 1 (Escuta em Tempo Real via Microfone) ", padding="8"
        )
        self._construir_m1_rx()

        # --- C) MÉTODO 2 - TRANSMISSOR ---
        self.frame_m2_tx = ttk.LabelFrame(
            self.frame_conteudo, text=" 2. Transmissor — Método 2 (Modulação FSK Contínua) ", padding="8"
        )
        self._construir_m2_tx()

        # --- D) MÉTODO 2 - RECEPTOR ---
        self.frame_m2_rx = ttk.LabelFrame(
            self.frame_conteudo, text=" 3. Receptor — Método 2 (Demodulação FSK via Microfone) ", padding="8"
        )
        self._construir_m2_rx()

        # 4. Banner de Status e Integridade
        self.lbl_status_banner = tk.Label(
            self.container,
            text="Sistema pronto para transmissão ou recepção.",
            font=("Arial", 11, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            pady=8,
            relief=tk.GROOVE,
        )
        self.lbl_status_banner.pack(fill=tk.X, pady=(0, 6))

        # 5. Painel de Diagnóstico e Log de Eventos
        frame_log = ttk.LabelFrame(self.container, text=" 4. Diagnóstico em Tempo Real e Log de Eventos ", padding="8")
        frame_log.pack(fill=tk.BOTH, expand=True)

        self.txt_diagnostico = tk.Text(frame_log, height=10, font=("Consolas", 9), wrap=tk.WORD)
        scroll = ttk.Scrollbar(frame_log, orient=tk.VERTICAL, command=self.txt_diagnostico.yview)
        self.txt_diagnostico.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_diagnostico.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # CONSTRUÇÃO DO PAINEL: MÉTODO 1 TX
    # --------------------------------------------------------------------------
    def _construir_m1_tx(self):
        f_msg = ttk.Frame(self.frame_m1_tx)
        f_msg.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(f_msg, text="Mensagem a Transmitir:").pack(side=tk.LEFT, padx=(0, 6))
        self.ent_m1_tx = ttk.Entry(f_msg, textvariable=self.var_mensagem_tx, width=24, font=("Consolas", 10))
        self.ent_m1_tx.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(
            f_msg,
            text="Injetar Erro Proposital de Paridade (Inverter 1 Bit)",
            variable=self.var_injetar_erro_m1,
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Botões de Transmissão
        f_acoes = ttk.Frame(self.frame_m1_tx)
        f_acoes.pack(fill=tk.X, pady=(2, 4))

        self.btn_transmitir_m1 = tk.Button(
            f_acoes,
            text="🔊 TRANSMITIR BATIDAS PELO ALTO-FALANTE",
            font=("Arial", 10, "bold"),
            bg="#0284c7",
            fg="white",
            padx=12,
            pady=5,
            command=self._transmitir_m1_auto,
        )
        self.btn_transmitir_m1.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_parar_tx_m1 = tk.Button(
            f_acoes,
            text="⏹️ Parar Transmissão",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=5,
            state=tk.DISABLED,
            command=self._parar_tx_m1,
        )
        self.btn_parar_tx_m1.pack(side=tk.LEFT)

        # Exibição de Quadros de 9 bits
        self.lbl_detalhes_m1_tx = tk.Label(
            self.frame_m1_tx,
            text="Quadros: aguardando...",
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#0f172a",
            anchor="w",
            justify=tk.LEFT,
            padx=8,
            pady=4,
            relief=tk.RIDGE,
        )
        self.lbl_detalhes_m1_tx.pack(fill=tk.X, pady=(2, 0))

    # --------------------------------------------------------------------------
    # CONSTRUÇÃO DO PAINEL: MÉTODO 1 RX
    # --------------------------------------------------------------------------
    def _construir_m1_rx(self):
        f_botoes = ttk.Frame(self.frame_m1_rx)
        f_botoes.pack(fill=tk.X, pady=(0, 4))

        self.btn_escutar_m1 = tk.Button(
            f_botoes,
            text="🎙️ INICIAR ESCUTA DO MICROFONE",
            font=("Arial", 10, "bold"),
            bg="#16a34a",
            fg="white",
            padx=12,
            pady=5,
            command=self._alternar_escuta_m1,
        )
        self.btn_escutar_m1.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_calibrar_m1 = tk.Button(
            f_botoes,
            text="🎚️ Calibrar Ruído Ambiente",
            font=("Arial", 9, "bold"),
            bg="#0284c7",
            fg="white",
            padx=8,
            pady=5,
            command=self._iniciar_calibracao,
        )
        self.btn_calibrar_m1.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_limpar_m1 = tk.Button(
            f_botoes,
            text="🔄 Limpar Recepção",
            font=("Arial", 9),
            bg="#475569",
            fg="white",
            padx=8,
            pady=5,
            command=self._limpar_dados_m1,
        )
        self.btn_limpar_m1.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(
            f_botoes,
            text="Modo Teste de Detecção (Apenas Batidas/Bits)",
            variable=self.var_modo_teste_m1,
        ).pack(side=tk.LEFT)

        # Sensibilidade, Volume e Status do Microfone
        f_sens = ttk.Frame(self.frame_m1_rx)
        f_sens.pack(fill=tk.X, pady=(2, 4))

        ttk.Label(f_sens, text="Limiar:").pack(side=tk.LEFT, padx=(0, 4))
        self.scale_limiar = ttk.Scale(
            f_sens, from_=0.02, to=0.30, orient=tk.HORIZONTAL, variable=self.var_limiar, length=140
        )
        self.scale_limiar.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_limiar_val = ttk.Label(f_sens, text="0.080", font=("Consolas", 9, "bold"))
        self.lbl_limiar_val.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(f_sens, text="Volume:").pack(side=tk.LEFT, padx=(0, 4))
        self.progress_volume = ttk.Progressbar(f_sens, orient=tk.HORIZONTAL, length=120, mode="determinate")
        self.progress_volume.pack(side=tk.LEFT, padx=(0, 12))

        self.lbl_mic_status = tk.Label(
            f_sens, text="● Microfone: INATIVO", font=("Arial", 9, "bold"), fg="#dc2626"
        )
        self.lbl_mic_status.pack(side=tk.LEFT)

        # Mensagem de Referência Opcional
        f_ref = ttk.Frame(self.frame_m1_rx)
        f_ref.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(f_ref, text="Mensagem de Referência (Opcional):").pack(side=tk.LEFT, padx=(0, 5))
        self.ent_ref_rx = ttk.Entry(f_ref, textvariable=self.var_msg_ref_rx, width=20, font=("Consolas", 10))
        self.ent_ref_rx.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_ref_bits_info = ttk.Label(
            f_ref,
            text="Recepção Livre: Nenhuma mensagem prévia necessária.",
            font=("Arial", 8, "italic"),
            foreground="#64748b",
        )
        self.lbl_ref_bits_info.pack(side=tk.LEFT)

        # Resumo de Bits e Mensagem Reconstruída
        f_resumo = ttk.Frame(self.frame_m1_rx)
        f_resumo.pack(fill=tk.X, pady=(2, 0))
        self.lbl_bits_rx_m1 = ttk.Label(
            f_resumo, text="Bits Recebidos: nenhum", font=("Consolas", 10, "bold")
        )
        self.lbl_bits_rx_m1.pack(side=tk.LEFT, padx=(0, 20))

        self.lbl_msg_rx_m1 = ttk.Label(
            f_resumo, text="Mensagem Reconstruída: \"\"", font=("Consolas", 10, "bold"), foreground="#1d4ed8"
        )
        self.lbl_msg_rx_m1.pack(side=tk.LEFT)

    # --------------------------------------------------------------------------
    # CONSTRUÇÃO DO PAINEL: MÉTODO 2 TX
    # --------------------------------------------------------------------------
    def _construir_m2_tx(self):
        # Seletor de Tipo de Entrada (Texto vs Batidas/Impactos)
        f_tipo_entrada = ttk.Frame(self.frame_m2_tx)
        f_tipo_entrada.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(f_tipo_entrada, text="Entrada de Dados:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(
            f_tipo_entrada,
            text="A) Entrada Automática (Digitar Mensagem)",
            variable=self.var_modo_entrada_m2,
            value="auto",
            command=self._ao_trocar_modo_entrada_m2,
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            f_tipo_entrada,
            text="B) Entrada Manual por Impactos (Palmas / Mesa no Microfone)",
            variable=self.var_modo_entrada_m2,
            value="impacto",
            command=self._ao_trocar_modo_entrada_m2,
        ).pack(side=tk.LEFT)

        # Subpainel A: Entrada de Texto Automático
        self.subframe_m2_tx_auto = ttk.Frame(self.frame_m2_tx)
        self.subframe_m2_tx_auto.pack(fill=tk.X, pady=(2, 4))

        f_txt = ttk.Frame(self.subframe_m2_tx_auto)
        f_txt.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(f_txt, text="Mensagem de Texto:").pack(side=tk.LEFT, padx=(0, 6))
        self.ent_m2_tx = ttk.Entry(f_txt, textvariable=self.var_mensagem_tx, width=24, font=("Consolas", 10))
        self.ent_m2_tx.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(
            f_txt,
            text="Injetar Erro Proposital no CRC-8 (1 Bit Invertido)",
            variable=self.var_injetar_erro_m2,
        ).pack(side=tk.LEFT)

        f_btn_auto = ttk.Frame(self.subframe_m2_tx_auto)
        f_btn_auto.pack(fill=tk.X, pady=2)

        self.btn_transmitir_fsk = tk.Button(
            f_btn_auto,
            text="🔊 TRANSMITIR ÁUDIO FSK (ALTO-FALANTE)",
            font=("Arial", 10, "bold"),
            bg="#0369a1",
            fg="white",
            padx=12,
            pady=5,
            command=self._transmitir_fsk_auto,
        )
        self.btn_transmitir_fsk.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_parar_fsk_tx = tk.Button(
            f_btn_auto,
            text="⏹️ Parar FSK",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=5,
            state=tk.DISABLED,
            command=self._parar_tx_fsk,
        )
        self.btn_parar_fsk_tx.pack(side=tk.LEFT)

        # Subpainel B: Entrada Manual por Impactos (Palmas/Batidas -> Bits -> FSK)
        self.subframe_m2_tx_impacto = ttk.Frame(self.frame_m2_tx)

        f_info_fluxo = tk.Label(
            self.subframe_m2_tx_impacto,
            text="Fluxo FSK com Batidas: Usuário Bate no Microfone (👏=0, 👏👏=1) → Bits Gerados → Codificador FSK → Transmissão no Alto-falante",
            font=("Arial", 8, "italic"),
            bg="#fef3c7",
            fg="#92400e",
            padx=6,
            pady=3,
        )
        f_info_fluxo.pack(fill=tk.X, pady=(0, 4))

        f_btn_imp = ttk.Frame(self.subframe_m2_tx_impacto)
        f_btn_imp.pack(fill=tk.X, pady=(0, 4))

        self.btn_escutar_impactos_m2 = tk.Button(
            f_btn_imp,
            text="🎙️ INICIAR CAPTURA DE BATIDAS PARA FSK",
            font=("Arial", 9, "bold"),
            bg="#d97706",
            fg="white",
            padx=10,
            pady=4,
            command=self._alternar_captura_impactos_m2_tx,
        )
        self.btn_escutar_impactos_m2.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_limpar_impactos_m2 = tk.Button(
            f_btn_imp,
            text="🔄 Limpar Bits Capturados",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=4,
            command=self._limpar_impactos_m2_tx,
        )
        self.btn_limpar_impactos_m2.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_transmitir_fsk_dos_impactos = tk.Button(
            f_btn_imp,
            text="🔊 MODULAR E TRANSMITIR BITS EM FSK",
            font=("Arial", 9, "bold"),
            bg="#0369a1",
            fg="white",
            padx=10,
            pady=4,
            command=self._transmitir_fsk_de_impactos,
        )
        self.btn_transmitir_fsk_dos_impactos.pack(side=tk.LEFT)

        self.lbl_impactos_m2_info = tk.Label(
            self.subframe_m2_tx_impacto,
            text="Bits Capturados por Batidas: nenhum | Aguardando início...",
            font=("Consolas", 9, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            anchor="w",
            padx=8,
            pady=4,
            relief=tk.RIDGE,
        )
        self.lbl_impactos_m2_info.pack(fill=tk.X, pady=(2, 0))

        # Rótulo de Detalhes FSK
        self.lbl_detalhes_m2_tx = tk.Label(
            self.frame_m2_tx,
            text="Parâmetros FSK: aguardando...",
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#0f172a",
            anchor="w",
            justify=tk.LEFT,
            padx=8,
            pady=4,
            relief=tk.RIDGE,
        )
        self.lbl_detalhes_m2_tx.pack(fill=tk.X, pady=(4, 0))

    # --------------------------------------------------------------------------
    # CONSTRUÇÃO DO PAINEL: MÉTODO 2 RX
    # --------------------------------------------------------------------------
    def _construir_m2_rx(self):
        f_botoes = ttk.Frame(self.frame_m2_rx)
        f_botoes.pack(fill=tk.X, pady=(0, 4))

        self.btn_receber_fsk = tk.Button(
            f_botoes,
            text="🎙️ CAPTAR ÁUDIO FSK PELO MICROFONE",
            font=("Arial", 10, "bold"),
            bg="#15803d",
            fg="white",
            padx=12,
            pady=5,
            command=self._receber_fsk_microfone,
        )
        self.btn_receber_fsk.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(f_botoes, text="Tempo de Escuta:").pack(side=tk.LEFT, padx=(0, 4))
        self.spin_dur_fsk = ttk.Spinbox(
            f_botoes, from_=2.0, to=20.0, increment=0.5, textvariable=self.var_duracao_fsk, width=5
        )
        self.spin_dur_fsk.pack(side=tk.LEFT, padx=(0, 15))

        self.btn_loopback_fsk = tk.Button(
            f_botoes,
            text="⚡ Loopback FSK (Teste Local sem Microfone)",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=5,
            command=self._loopback_fsk,
        )
        self.btn_loopback_fsk.pack(side=tk.LEFT)

        # Informações da Demodulação FSK
        self.lbl_demod_fsk_info = tk.Label(
            self.frame_m2_rx,
            text="Frequências: 0=1200 Hz | 1=2200 Hz | Preâmbulo=1700 Hz (Filtro Casado) | Aguardando captura...",
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#0f172a",
            anchor="w",
            justify=tk.LEFT,
            padx=8,
            pady=4,
            relief=tk.RIDGE,
        )
        self.lbl_demod_fsk_info.pack(fill=tk.X, pady=(2, 0))

    # ==========================================================================
    # VISIBILIDADE DOS PAINÉIS
    # ==========================================================================
    def _ao_trocar_metodo(self):
        self._parar_tudo_se_ativo()
        self._atualizar_visibilidade_paineis()
        self._definir_status(
            f"{'Método 1 Selecionado: Batidas por Impacto' if self.var_metodo.get() == 'metodo1' else 'Método 2 Selecionado: Modulação FSK Contínua'}",
            "#e0f2fe",
            "#0369a1",
        )

    def _ao_trocar_papel(self):
        self._parar_tudo_se_ativo()
        self._atualizar_visibilidade_paineis()

    def _ao_trocar_modo_entrada_m2(self):
        if self.var_modo_entrada_m2.get() == "auto":
            self.subframe_m2_tx_impacto.pack_forget()
            self.subframe_m2_tx_auto.pack(fill=tk.X, pady=(2, 4))
        else:
            self.subframe_m2_tx_auto.pack_forget()
            self.subframe_m2_tx_impacto.pack(fill=tk.X, pady=(2, 4))

    def _atualizar_visibilidade_paineis(self):
        metodo = self.var_metodo.get()
        papel = self.var_papel.get()

        # Oculta todos primeiro
        self.frame_m1_tx.pack_forget()
        self.frame_m1_rx.pack_forget()
        self.frame_m2_tx.pack_forget()
        self.frame_m2_rx.pack_forget()

        if metodo == "metodo1":
            if papel in ("tx", "ambos"):
                self.frame_m1_tx.pack(fill=tk.X, pady=(0, 6))
            if papel in ("rx", "ambos"):
                self.frame_m1_rx.pack(fill=tk.X, pady=(0, 6))
        else:
            if papel in ("tx", "ambos"):
                self.frame_m2_tx.pack(fill=tk.X, pady=(0, 6))
                self._ao_trocar_modo_entrada_m2()
            if papel in ("rx", "ambos"):
                self.frame_m2_rx.pack(fill=tk.X, pady=(0, 6))

    def _parar_tudo_se_ativo(self):
        if self.escutando_tempo_real_m1:
            self._alternar_escuta_m1()
        if self.escutando_impactos_m2_tx:
            self._alternar_captura_impactos_m2_tx()
        self._parar_tx_m1()
        self._parar_tx_fsk()

    def _definir_status(self, texto: str, cor_fundo: str = "#f1f5f9", cor_texto: str = "#0f172a"):
        self.lbl_status_banner.config(text=texto, bg=cor_fundo, fg=cor_texto)

    def _log_diagnostico(self, texto: str, limpar: bool = False):
        if limpar:
            self.txt_diagnostico.delete("1.0", tk.END)
        self.txt_diagnostico.insert(tk.END, texto + "\n")
        self.txt_diagnostico.see(tk.END)

    # ==========================================================================
    # MÉTODO 1 — LÓGICA DO TRANSMISSOR (TX)
    # ==========================================================================
    def _atualizar_detalhes_tx_m1(self):
        msg = self.var_mensagem_tx.get()
        if not msg:
            self.lbl_detalhes_m1_tx.config(text="Digite uma mensagem para gerar os quadros de 9 bits.")
            return

        linhas = ["QUADROS DE 9 BITS PARA TRANSMISSÃO (8 bits de dados + 1 bit de paridade par):"]
        bits_totais = []
        for i, char in enumerate(msg):
            b_char = mensagem_para_bits(char)
            quadro = criar_quadro_metodo1(b_char)
            p = quadro[-1]
            linhas.append(f"  Quadro {i+1} ('{char}') -> Dados: {''.join(str(b) for b in quadro[:8])} | Paridade Par: {p} -> Quadro: {''.join(str(b) for b in quadro)}")
            bits_totais.extend(quadro)

        if self.var_injetar_erro_m1.get() and bits_totais:
            bits_totais[0] = 1 - bits_totais[0]
            linhas.append("  ⚠ [ERRO INJETADO] O 1º bit foi invertido propositalmente para simular falha de paridade!")

        str_totais = "".join(str(b) for b in bits_totais)
        linhas.append(f"Sequência Completa ({len(bits_totais)} bits): {str_totais}")
        linhas.append("Legenda: 1 batida (👏) = Bit 0  |  2 batidas consecutivas (👏👏) = Bit 1")
        self.lbl_detalhes_m1_tx.config(text="\n".join(linhas))

    def _transmitir_m1_auto(self):
        msg = self.var_mensagem_tx.get().strip() or "OI"
        bits_tx = codificar_mensagem_metodo1(mensagem_para_bits(msg))
        if self.var_injetar_erro_m1.get() and bits_tx:
            bits_tx[0] = 1 - bits_tx[0]

        def tarefa():
            self.transmitindo_m1 = True
            self.after(0, lambda: self.btn_transmitir_m1.config(state=tk.DISABLED))
            self.after(0, lambda: self.btn_parar_tx_m1.config(state=tk.NORMAL))
            self._definir_status(f"Sintetizando e emitindo batidas para '{msg}' ({len(bits_tx)} bits)...", "#fef08a", "#854d0e")
            self._log_diagnostico(f"\n=== TRANSMISSÃO AUTOMÁTICA MÉTODO 1 ===")
            self._log_diagnostico(f"Mensagem: '{msg}' | Total de bits (9 por quadro): {len(bits_tx)}")
            self._log_diagnostico(f"Sequência emitida:\n{formatar_bits(bits_tx, 9)}")
            self._log_diagnostico("[*] Reproduzindo batidas sintéticas nos alto-falantes...")

            try:
                audio = sintetizar_bits_metodo1(bits_tx, sample_rate=44100, tempo_bit=0.7)
                self._definir_status(f"Emitindo batidas acústicas no alto-falante ({len(bits_tx)} bits)...", "#93c5fd", "#1e3a8a")
                transmitir_audio_metodo1(audio, sample_rate=44100)
                if self.transmitindo_m1:
                    self._definir_status("✓ Transmissão de batidas concluída com sucesso!", "#bbf7d0", "#166534")
                    self._log_diagnostico("[✓] Transmissão acústica finalizada.")
            except Exception as e:
                self._definir_status(f"Erro na transmissão de áudio: {e}", "#fee2e2", "#991b1b")
                self._log_diagnostico(f"[!] Erro ao reproduzir som: {e}")
            finally:
                self.transmitindo_m1 = False
                self.after(0, lambda: self.btn_transmitir_m1.config(state=tk.NORMAL))
                self.after(0, lambda: self.btn_parar_tx_m1.config(state=tk.DISABLED))

        threading.Thread(target=tarefa, daemon=True).start()

    def _parar_tx_m1(self):
        self.transmitindo_m1 = False
        parar_transmissao_metodo1()
        self.btn_transmitir_m1.config(state=tk.NORMAL)
        self.btn_parar_tx_m1.config(state=tk.DISABLED)
        self._definir_status("Transmissão de batidas cancelada.", "#f1f5f9", "#475569")
        self._log_diagnostico("[*] Transmissão interrompida pelo usuário.")

    # ==========================================================================
    # MÉTODO 1 — LÓGICA DO RECEPTOR (RX EM TEMPO REAL)
    # ==========================================================================
    def _alternar_escuta_m1(self):
        if not self.escutando_tempo_real_m1:
            try:
                self.detector_m1.definir_limiar(self.var_limiar.get())
                self.detector_m1.iniciar()
                self.escutando_tempo_real_m1 = True
                self.btn_escutar_m1.config(text="⏹️ PARAR ESCUTA DO MICROFONE", bg="#dc2626")
                self.lbl_mic_status.config(text="● Microfone: ATIVO", fg="#16a34a")
                self._definir_status("Microfone ATIVO: Escutando batidas reais (👏=0, 👏👏=1)...", "#dcfce7", "#15803d")
                self._log_diagnostico("\n[*] Microfone iniciado! Escutando batidas acústicas...")
            except Exception as e:
                messagebox.showerror("Erro de Microfone", f"Não foi possível abrir o dispositivo de áudio:\n{e}")
        else:
            self.detector_m1.parar()
            self.escutando_tempo_real_m1 = False
            self.btn_escutar_m1.config(text="🎙️ INICIAR ESCUTA DO MICROFONE", bg="#16a34a")
            self.lbl_mic_status.config(text="● Microfone: INATIVO", fg="#dc2626")
            self.progress_volume["value"] = 0
            self._definir_status("Microfone parado.", "#f1f5f9", "#475569")
            self._log_diagnostico("[*] Escuta encerrada.")

    def _ao_receber_bit_m1(self, bit: int, descricao: str):
        self.after(0, lambda: self._processar_bit_m1_interface(bit, descricao))

    def _processar_bit_m1_interface(self, bit: int, descricao: str):
        self.total_batidas_m1 += 1
        self.bits_recebidos_m1.append(bit)
        str_bits_total = "".join(str(b) for b in self.bits_recebidos_m1)
        self.lbl_bits_rx_m1.config(text=f"Bits Recebidos: {str_bits_total} ({len(self.bits_recebidos_m1)})")

        if self.var_modo_teste_m1.get():
            self._log_diagnostico(f"-> {descricao.upper()} -> BIT: {bit}")
            self._definir_status(f"Bit {bit} detectado ({descricao})", "#dbeafe", "#1d4ed8")
            return

        pos_no_quadro = len(self.bits_recebidos_m1) % 9
        if pos_no_quadro == 0:
            pos_no_quadro = 9
        idx_quadro = (len(self.bits_recebidos_m1) - 1) // 9 + 1

        self._log_diagnostico(f"-> {descricao} -> Bit {bit} | Quadro {idx_quadro} ({pos_no_quadro}/9)")
        self._definir_status(f"Bit {bit} recebido ({descricao}) - Quadro {idx_quadro} ({pos_no_quadro}/9)", "#fef9c3", "#854d0e")

        if pos_no_quadro == 9:
            quadro_9 = self.bits_recebidos_m1[-9:]
            sucesso, dados_8, p_esp, p_rec = verificar_quadro_metodo1(quadro_9)
            str_quadro = "".join(str(b) for b in quadro_9)
            str_dados = "".join(str(b) for b in dados_8)

            if sucesso:
                char_byte = bits_para_bytes(dados_8)
                char_str = char_byte.decode("latin-1", errors="replace")
                self.mensagem_reconstruida_m1 += char_str
                self.lbl_msg_rx_m1.config(text=f"Mensagem Reconstruída: \"{self.mensagem_reconstruida_m1}\"")

                self._log_diagnostico(
                    f"\n[✓ QUADRO {idx_quadro} ÍNTEGRO]\n"
                    f"  Quadro: {str_quadro}\n"
                    f"  Dados: {str_dados}\n"
                    f"  Paridade: {p_rec} (Esperada: {p_esp}) -> ✓ PARIDADE PAR CORRETA\n"
                    f"  Caractere Decodificado: '{char_str}'\n"
                    f"  Mensagem Acumulada: '{self.mensagem_reconstruida_m1}'\n"
                )
                self._definir_status(f"✓ QUADRO {idx_quadro} VALIDADO: '{char_str}'", "#bbf7d0", "#166534")

                ref = self.var_msg_ref_rx.get().strip()
                if ref and len(self.mensagem_reconstruida_m1) == len(ref):
                    if self.mensagem_reconstruida_m1 == ref:
                        self._definir_status(f"✓ SUCESSO TOTAL: Mensagem idêntica à referência '{ref}'!", "#22c55e", "white")
                        self._log_diagnostico(f"\n🎉 SUCESSO TOTAL: Mensagem '{ref}' reconstruída e validada!\n")
                    else:
                        self._definir_status(f"⚠ Divergência: Esperado '{ref}', Recebido '{self.mensagem_reconstruida_m1}'", "#f97316", "white")
            else:
                self._log_diagnostico(
                    f"\n[✗ QUADRO {idx_quadro} COM FALHA DE PARIDADE]\n"
                    f"  Quadro: {str_quadro}\n"
                    f"  Paridade Recebida: {p_rec} != Esperada: {p_esp}\n"
                    f"  ✗ FALHA DE TRANSMISSÃO — Dados corrompidos no canal acústico!\n"
                )
                self._definir_status(f"✗ FALHA DE TRANSMISSÃO — Paridade Inválida no Quadro {idx_quadro}!", "#ef4444", "white")

    def _ao_receber_evento_m1(self, tipo: str, info: Dict[str, Any]):
        if tipo == "NIVEL_AUDIO":
            pico = info.get("pico", 0.0)
            limiar = info.get("limiar", 0.08)
            pct = min(100, int((pico / max(0.01, limiar * 1.5)) * 100))
            self.after(0, lambda: self.progress_volume.configure(value=pct))
        elif tipo == "PRIMEIRA_BATIDA":
            self.after(0, lambda: self._definir_status("👏 Primeira batida! Aguardando 2ª batida...", "#fed7aa", "#9a3412"))

    def _iniciar_calibracao(self):
        def tarefa():
            self._definir_status("Calibrando microfone... Fique em silêncio por 1.5s", "#fed7aa", "#9a3412")
            self._log_diagnostico("\n[*] Medindo ruído ambiente por 1.5s...")
            try:
                ruido, limiar = self.detector_m1.calibrar_ruido(duracao_s=1.5)
                self.after(0, lambda: self.var_limiar.set(round(limiar, 3)))
                self.after(0, lambda: self.lbl_limiar_val.config(text=f"{limiar:.3f}"))
                self.after(0, lambda: self._definir_status(f"Calibração Concluída! Ruído: {ruido:.3f} | Novo Limiar: {limiar:.3f}", "#bbf7d0", "#166534"))
                self._log_diagnostico(f"[+] Ruído medido: {ruido:.4f} | Limiar ajustado para: {limiar:.4f}")
            except Exception as e:
                self._log_diagnostico(f"[!] Erro ao calibrar microfone: {e}")

        threading.Thread(target=tarefa, daemon=True).start()

    def _limpar_dados_m1(self):
        self.bits_recebidos_m1 = []
        self.mensagem_reconstruida_m1 = ""
        self.total_batidas_m1 = 0
        self.lbl_bits_rx_m1.config(text="Bits Recebidos: nenhum")
        self.lbl_msg_rx_m1.config(text="Mensagem Reconstruída: \"\"")
        self._definir_status("Recepção reiniciada. Pronto para captar novos sons.", "#f1f5f9", "#0f172a")
        self._log_diagnostico("\n[REINÍCIO] Dados do Método 1 reiniciados.")

    # ==========================================================================
    # MÉTODO 2 — LÓGICA DO TRANSMISSOR (FSK TX)
    # ==========================================================================
    def _atualizar_detalhes_tx_m2(self):
        msg = self.var_mensagem_tx.get().strip() or "OI"
        try:
            bits_tx = codificar_mensagem_metodo2(msg)
            if self.var_injetar_erro_m2.get():
                bits_tx = injetar_erro_de_bit(bits_tx, indice=10)

            taxas = calcular_taxa_bps(len(msg) * 8, len(bits_tx))
            linhas = [
                f"Modulação FSK: Bit 0 = {FREQ_BIT_0:.0f} Hz | Bit 1 = {FREQ_BIT_1:.0f} Hz | Preâmbulo = {FREQ_PREAMBULO:.0f} Hz",
                f"Mensagem: '{msg}' | Pacote com CRC-8: {len(bits_tx)} bits ({len(bits_tx)//8} bytes)",
                f"Taxa Teórica: {taxas['taxa_teorica_bps']} bps | Taxa Prática: {taxas['taxa_pratica_bps']} bps | Duração: {taxas['duracao_total_s']}s",
            ]
            if self.var_injetar_erro_m2.get():
                linhas.append("⚠ [ALERTA] Injeção de erro de 1 bit ativada (simular falha no CRC-8)!")
            self.lbl_detalhes_m2_tx.config(text="\n".join(linhas))
        except Exception as e:
            self.lbl_detalhes_m2_tx.config(text=f"Erro ao montar pacote FSK: {e}")

    def _transmitir_fsk_auto(self):
        msg = self.var_mensagem_tx.get().strip() or "OI"
        injetar_erro = self.var_injetar_erro_m2.get()

        def tarefa():
            self.transmitindo_m2 = True
            self.after(0, lambda: self.btn_transmitir_fsk.config(state=tk.DISABLED))
            self.after(0, lambda: self.btn_parar_fsk_tx.config(state=tk.NORMAL))
            self._definir_status(f"Sintetizando sinal FSK para '{msg}'...", "#fef08a", "#854d0e")

            bits_tx = codificar_mensagem_metodo2(msg)
            if injetar_erro:
                bits_tx = injetar_erro_de_bit(bits_tx, indice=10)

            audio = sintetizar_bits_fsk(bits_tx, sample_rate=44100)
            self.ultimo_audio_fsk = audio
            self.ultimos_bits_fsk = bits_tx

            self._log_diagnostico(f"\n=== TRANSMISSÃO FSK ===")
            self._log_diagnostico(f"Mensagem: '{msg}' | Bits Totais: {len(bits_tx)}")
            self._log_diagnostico(f"Bits:\n{formatar_bits(bits_tx, 8)}")
            if injetar_erro:
                self._log_diagnostico("⚠ [ALERTA] 1 Bit invertido propositalmente para simular falha no CRC-8!")

            self._definir_status("Transmitindo sinal FSK nos alto-falantes...", "#93c5fd", "#1e3a8a")
            try:
                transmitir_audio_fsk(audio, sample_rate=44100)
                if self.transmitindo_m2:
                    self._definir_status("✓ Transmissão FSK concluída com sucesso!", "#bbf7d0", "#166534")
                    self._log_diagnostico("[✓] Transmissão FSK finalizada.")
            except Exception as e:
                self._definir_status(f"Erro na transmissão FSK: {e}", "#fee2e2", "#991b1b")
                self._log_diagnostico(f"[!] Erro ao emitir FSK: {e}")
            finally:
                self.transmitindo_m2 = False
                self.after(0, lambda: self.btn_transmitir_fsk.config(state=tk.NORMAL))
                self.after(0, lambda: self.btn_parar_fsk_tx.config(state=tk.DISABLED))

        threading.Thread(target=tarefa, daemon=True).start()

    def _parar_tx_fsk(self):
        self.transmitindo_m2 = False
        parar_transmissao_fsk()
        self.btn_transmitir_fsk.config(state=tk.NORMAL)
        self.btn_parar_fsk_tx.config(state=tk.DISABLED)
        self._definir_status("Transmissão FSK interrompida.", "#f1f5f9", "#475569")
        self._log_diagnostico("[*] Emissão FSK cancelada.")

    # --------------------------------------------------------------------------
    # MÉTODO 2 TX — ENTRADA MANUAL POR IMPACTOS (Seção 3 da correção)
    # --------------------------------------------------------------------------
    def _alternar_captura_impactos_m2_tx(self):
        if not self.escutando_impactos_m2_tx:
            try:
                self.detector_m2_impactos.definir_limiar(self.var_limiar.get())
                self.detector_m2_impactos.iniciar()
                self.escutando_impactos_m2_tx = True
                self.btn_escutar_impactos_m2.config(text="⏹️ FINALIZAR CAPTURA DE BATIDAS", bg="#dc2626")
                self._definir_status("Microfone ATIVO para entrada FSK: Bate 1 vez para 0, 2 vezes para 1!", "#fef3c7", "#92400e")
                self._log_diagnostico("\n[*] Microfone aberto para captura de bits via impactos (para posterior FSK)...")
            except Exception as e:
                messagebox.showerror("Erro de Microfone", f"Não foi possível abrir o microfone:\n{e}")
        else:
            self.detector_m2_impactos.parar()
            self.escutando_impactos_m2_tx = False
            self.btn_escutar_impactos_m2.config(text="🎙️ INICIAR CAPTURA DE BATIDAS PARA FSK", bg="#d97706")
            self._definir_status("Captura de batidas encerrada. Clique em 'Modular e Transmitir via FSK'.", "#dcfce7", "#166534")
            self._log_diagnostico(f"[*] Captura de batidas encerrada. Total de bits coletados: {len(self.bits_impactos_m2_tx)}")

    def _ao_receber_bit_m2_tx(self, bit: int, descricao: str):
        self.after(0, lambda: self._processar_bit_m2_tx(bit, descricao))

    def _processar_bit_m2_tx(self, bit: int, descricao: str):
        self.bits_impactos_m2_tx.append(bit)
        str_bits = "".join(str(b) for b in self.bits_impactos_m2_tx)
        txt_equiv = ""
        if len(self.bits_impactos_m2_tx) >= 8:
            txt_equiv = f" | Texto: '{bits_para_mensagem(self.bits_impactos_m2_tx)}'"

        self.lbl_impactos_m2_info.config(
            text=f"Bits Capturados: {str_bits} ({len(self.bits_impactos_m2_tx)} bits){txt_equiv}"
        )
        self._definir_status(f"Bit {bit} capturado ({descricao}) para transmissão FSK", "#fed7aa", "#9a3412")
        self._log_diagnostico(f"[Entrada FSK via Batida] {descricao} -> Bit {bit} (Total: {len(self.bits_impactos_m2_tx)})")

    def _ao_receber_evento_m2_tx(self, tipo: str, info: Dict[str, Any]):
        if tipo == "NIVEL_AUDIO":
            pico = info.get("pico", 0.0)
            limiar = info.get("limiar", 0.08)
            pct = min(100, int((pico / max(0.01, limiar * 1.5)) * 100))
            self.after(0, lambda: self.progress_volume.configure(value=pct))

    def _limpar_impactos_m2_tx(self):
        self.bits_impactos_m2_tx = []
        self.lbl_impactos_m2_info.config(text="Bits Capturados por Batidas: nenhum | Aguardando início...")
        self._definir_status("Bits de impacto limpos.", "#f1f5f9", "#0f172a")

    def _transmitir_fsk_de_impactos(self):
        if not self.bits_impactos_m2_tx:
            messagebox.showinfo("Aviso", "Capture ao menos alguns bits por batidas antes de modular em FSK!")
            return

        bits_entrada = list(self.bits_impactos_m2_tx)
        injetar_erro = self.var_injetar_erro_m2.get()

        def tarefa():
            # Converte bits em bytes e adiciona cabeçalho + CRC-8
            # Se não for múltiplo de 8, completa com zeros à direita
            resto = len(bits_entrada) % 8
            if resto != 0:
                qtd_preenchimento = 8 - resto
                bits_entrada.extend([0] * qtd_preenchimento)
                self._log_diagnostico(f"[*] Ajuste: {len(self.bits_impactos_m2_tx)} bits capturados preenchidos com {qtd_preenchimento} zeros à direita para formar {len(bits_entrada)} bits ({len(bits_entrada)//8} bytes).")

            dados_bytes = bits_para_bytes(bits_entrada)
            pacote = montar_pacote_metodo2(dados_bytes)
            bits_fsk = bytes_para_bits(pacote)

            if injetar_erro:
                bits_fsk = injetar_erro_de_bit(bits_fsk, indice=10)

            self.ultimo_audio_fsk = sintetizar_bits_fsk(bits_fsk, sample_rate=44100)
            self.ultimos_bits_fsk = bits_fsk

            self._log_diagnostico(f"\n=== TRANSMISSÃO FSK A PARTIR DE BATIDAS MANUAIS ===")
            self._log_diagnostico(f"Bits originados fisicamente por batidas: {''.join(str(b) for b in self.bits_impactos_m2_tx)}")
            self._log_diagnostico(f"Pacote FSK com CRC-8 ({len(bits_fsk)} bits):\n{formatar_bits(bits_fsk, 8)}")
            self._definir_status("Transmitindo sinal FSK (originado de batidas) no alto-falante...", "#93c5fd", "#1e3a8a")

            try:
                transmitir_audio_fsk(self.ultimo_audio_fsk, sample_rate=44100)
                self._definir_status("✓ Transmissão FSK de batidas manuais concluída!", "#bbf7d0", "#166534")
                self._log_diagnostico("[✓] Sinal FSK emitido com sucesso nos alto-falantes.")
            except Exception as e:
                self._definir_status(f"Erro na transmissão: {e}", "#fee2e2", "#991b1b")
                self._log_diagnostico(f"[!] Erro ao emitir áudio FSK: {e}")

        threading.Thread(target=tarefa, daemon=True).start()

    # ==========================================================================
    # MÉTODO 2 — LÓGICA DO RECEPTOR (FSK RX)
    # ==========================================================================
    def _receber_fsk_microfone(self):
        duracao = float(self.var_duracao_fsk.get())

        def tarefa():
            self.after(0, lambda: self.btn_receber_fsk.config(
                text=f"🎙️ ESCUTANDO ({duracao:.1f}s)...", state=tk.DISABLED, bg="#d97706"
            ))
            self._definir_status(
                f"🎙️ Escutando microfone ({duracao:.1f}s)... AGUARDANDO TRANSMISSÃO FSK (Inicie no PC transmissor!)",
                "#fef08a",
                "#854d0e"
            )
            self._log_diagnostico(f"\n[*] Gravando canal FSK pelo microfone ({duracao:.1f} segundos)...")
            self._log_diagnostico("[*] Receptor ativo. Aguardando emissão do tom piloto de 1700 Hz...")

            try:
                sinal = gravar_audio_microfone_fsk(duracao, sample_rate=44100)
                self._definir_status("🔍 Áudio captado! Analisando espectro e buscando preâmbulo de 1700 Hz...", "#93c5fd", "#1e3a8a")
                self._processar_fsk_recebido(sinal)
            except Exception as e:
                self._definir_status(f"Erro ao capturar áudio FSK: {e}", "#fee2e2", "#991b1b")
                self._log_diagnostico(f"[!] Falha na gravação do microfone: {e}")
            finally:
                self.after(0, lambda: self.btn_receber_fsk.config(
                    text="🎙️ CAPTAR ÁUDIO FSK PELO MICROFONE", state=tk.NORMAL, bg="#15803d"
                ))

        threading.Thread(target=tarefa, daemon=True).start()

    def _loopback_fsk(self):
        if self.ultimo_audio_fsk is None:
            messagebox.showinfo("Aviso", "Transmita primeiro um sinal FSK para gerar o áudio de loopback.")
            return
        self._log_diagnostico("\n=== TESTE DE LOOPBACK FSK (INTERNO) ===")
        self._processar_fsk_recebido(self.ultimo_audio_fsk)

    def _processar_fsk_recebido(self, sinal: np.ndarray):
        bits_rx, diag = decodificar_audio_fsk(sinal, sample_rate=44100, retornar_diagnostico=True)

        if not bits_rx:
            self._log_diagnostico("[!] Nenhum sinal piloto FSK (1700 Hz) detectado no áudio capturado.")
            self._log_diagnostico("    - O receptor ignorou o ruído ambiente para evitar decodificar dados inválidos.")
            self._log_diagnostico("    - Dica: Verifique se a transmissão no PC transmissor ocorreu durante o tempo de escuta.")
            self._definir_status("✗ Falha de Recepção: Nenhum preâmbulo FSK (1700 Hz) detectado no microfone!", "#fee2e2", "#991b1b")
            self.lbl_demod_fsk_info.config(
                text="Demodulação FSK: Nenhum preâmbulo localizado no sinal capturado (ruído descartado)."
            )
            return

        t_ini = diag.get("tempo_inicio_s", 0.0)
        conf_med = diag.get("confianca_media", 0.0)
        self._log_diagnostico(f"[✓] Preâmbulo FSK (1700 Hz) detectado com sucesso!")
        self._log_diagnostico(f"    Sincronismo de dados alinhado em t = {t_ini:.3f}s | Confiança média: {conf_med:.1f}%")
        self._log_diagnostico(f"Bits demodulados do áudio ({len(bits_rx)} bits):\n{formatar_bits(bits_rx, 8)}")

        # Log de diagnóstico com amostra dos símbolos
        simbolos = diag.get("simbolos", [])
        if simbolos:
            self._log_diagnostico("--- Amostra do Diagnóstico Espectral dos Símbolos ---")
            for s in simbolos[:8]:
                f_nome = "2200 Hz" if s["bit"] == 1 else "1200 Hz"
                self._log_diagnostico(f"  Símbolo {s['simbolo']:02d} [{s['tempo_s']:.3f}s] -> bit {s['bit']} ({f_nome}) | Confiança: {s['confianca']:.1f}%")
            if len(simbolos) > 8:
                self._log_diagnostico(f"  ... (+ {len(simbolos)-8} símbolos demodulados)")

        relatorio = decodificar_bits_metodo2(bits_rx)

        self._log_diagnostico(f"CRC-8 Calculado: {relatorio['crc_calculado']} | Recebido: {relatorio['crc_recebido']}")
        self._log_diagnostico(f"Status: {relatorio['status']}")

        info_lbl = f"Demodulação: {len(bits_rx)} bits | Confiança: {conf_med:.1f}% | CRC Calc: {relatorio['crc_calculado']} vs Rec: {relatorio['crc_recebido']}"
        self.lbl_demod_fsk_info.config(text=info_lbl)

        if relatorio["sucesso"]:
            msg = relatorio["mensagem"]
            self._log_diagnostico(f"[✓ SUCESSO] Mensagem Reconstruída: '{msg}'")
            self._definir_status(f"✓ SUCESSO — Integridade Validada via CRC-8: '{msg}'", "#22c55e", "white")
        else:
            self._log_diagnostico("[✗ FALHA] Pacote corrompido! O CRC-8 acusou divergência de integridade.")
            self._definir_status(f"✗ {relatorio['status']}", "#ef4444", "white")


def iniciar_interface():
    app = AppCamadaFisica()
    app.mainloop()


if __name__ == "__main__":
    iniciar_interface()
